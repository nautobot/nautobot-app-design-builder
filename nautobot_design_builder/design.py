"""Provides ORM interaction for design builder."""

from collections import defaultdict, OrderedDict
from types import FunctionType
from typing import Any, Dict, List, Mapping, Type, Union

from django.apps import apps
from django.db.models import Model, Manager
from django.db.models.fields import Field as DjangoField
from django.dispatch.dispatcher import Signal
from django.core.exceptions import ObjectDoesNotExist, ValidationError, MultipleObjectsReturned
from django.db import transaction


from nautobot.core.graphql.utils import str_to_var_name
from nautobot.extras.models import JobResult, Relationship
from nautobot.utilities.utils import shallow_compare_dict
from nautobot.extras.api.serializers import StatusModelSerializerMixin
from nautobot.extras.api.fields import StatusSerializerField
from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.extras.models import Status

from nautobot_design_builder import errors
from nautobot_design_builder import ext
from nautobot_design_builder.logging import LoggingMixin, get_logger
from nautobot_design_builder.fields import field_factory, OneToOneField, ManyToOneField
from nautobot_design_builder import models
from nautobot_design_builder.constants import NAUTOBOT_ID
from nautobot_design_builder.util import nautobot_version
from nautobot_design_builder.recursive import inject_nautobot_uuids, get_object_identifier


if nautobot_version < "2.0.0":
    # This overwrite is a workaround for a Nautobot 1.6 Serializer limitation for Status
    # https://github.com/nautobot/nautobot/blob/ltm-1.6/nautobot/extras/api/fields.py#L22
    from nautobot.utilities.api import get_serializer_for_model  # pylint: disable=ungrouped-imports
    from nautobot.utilities.utils import serialize_object  # pylint: disable=ungrouped-imports

    def serialize_object_v2(obj):
        """
        Custom Implementation. Not needed for Nautobot 2.0.

        Return a JSON serialized representation of an object using obj's serializer.
        """

        class CustomStatusSerializerField(StatusSerializerField):
            """CustomStatusSerializerField."""

            def to_representation(self, obj):
                """Make this field compatible w/ the existing API for `ChoiceField`."""
                if obj == "":
                    return None

                return OrderedDict([("value", obj.slug), ("label", str(obj)), ("id", str(obj.id))])

        class CustomStatusModelSerializerMixin(StatusModelSerializerMixin):
            """Mixin to add `status` choice field to model serializers."""

            status = CustomStatusSerializerField(queryset=Status.objects.all())

        # Try serializing obj(model instance) using its API Serializer
        try:
            serializer_class = get_serializer_for_model(obj.__class__)
            if issubclass(serializer_class, StatusModelSerializerMixin):

                class NewSerializerClass(CustomStatusModelSerializerMixin, serializer_class):
                    """Custom SerializerClass."""

                serializer_class = NewSerializerClass
            data = serializer_class(obj, context={"request": None, "depth": 1}).data
        except SerializerNotFound:
            # Fall back to generic JSON representation of obj
            data = serialize_object(obj)

        return data

else:
    from nautobot.core.models.utils import serialize_object_v2  # pylint: disable=import-error,no-name-in-module


# TODO: Refactor this code into the Journal model
class Journal:
    """Keep track of the objects created or updated during the course of a design's implementation.

    The Journal provides a way to do post-implementation processing. For
    instance, if every item created in a design needs to be updated with
    a tag, then a post_implementation method can be created in the
    job and the journal.created items can be iterated and updated. The
    Journal contains three indices:

    index: a set of all the model UUIDs that have been created or updated

    created: a dictionary of objects created. The keys of this index are
    model classes and the values are sets of primary key UUIDs

    updated: like created, this index is a dictionary of objects that
    have been updated. The keys are model classes and the values are the primary
    key UUIDs

    An object's UUID may appear in both created and updated. However, they
    will only be in each of those indices at most once.
    """

    def __init__(self, design_journal: models.Journal = None):
        """Constructor for Journal object."""
        self.index = set()
        self.created = defaultdict(set)
        self.updated = defaultdict(set)
        self.design_journal = design_journal

    def log(self, model: "ModelInstance"):
        """Log that a model has been created or updated.

        Args:
            model (BaseModel): The model that has been created or updated
        """
        instance = model.instance
        model_type = instance.__class__
        if self.design_journal:
            self.design_journal.log(model)

        if instance.pk not in self.index:
            self.index.add(instance.pk)
            if model.created:
                index = self.created
            else:
                index = self.updated

            index.setdefault(model_type, set())
            index[model_type].add(instance.pk)

    @property
    def created_objects(self) -> Dict[str, List[Model]]:
        """Return a dictionary of Nautobot objects that were created.

        Returns:
            Dict[str, List[BaseModel]]: A dictionary of created objects. The
            keys of the dictionary are the lower case content type labels
            (such as `dcim.device`) and the values are lists of created objects
            of the corresponding type.
        """
        results = {}
        for model_type, pk_list in self.created.items():
            object_list = []
            for primary_key in pk_list:
                instance = model_type.objects.get(pk=primary_key)
                object_list.append(instance)
            results[model_type._meta.label_lower] = object_list
        return results


def _map_query_values(query: Mapping) -> Mapping:
    retval = {}
    for key, value in query.items():
        if isinstance(value, ModelInstance):
            retval[key] = value.instance
        elif isinstance(value, Mapping):
            retval[key] = _map_query_values(value)
        else:
            retval[key] = value
    return retval


def calculate_changes(current_state, initial_state=None, created=False, pre_change=False):
    """Determine the differences between the original instance and the current.

    This will calculate the changes between the instance's initial state
    and its current state. If pre_change is supplied it will use this
    dictionary as the initial state rather than the current ModelInstance
    initial state.

    Args:
        pre_change (dict, optional): Initial state for comparison. If not supplied then the initial state from this instance is used.

    Returns:
        Return a dictionary with the changed object's serialized data compared
        with either the model instance initial state, or the supplied pre_change
        state. The dictionary has the following values:

        dict: {
            "prechange": dict(),
            "postchange": dict(),
            "differences": {
                "removed": dict(),
                "added": dict(),
            }
        }
    """
    post_change = serialize_object_v2(current_state)

    if not created and not pre_change:
        pre_change = initial_state

    if pre_change and post_change:
        diff_added = shallow_compare_dict(pre_change, post_change, exclude=["last_updated"])
        diff_removed = {x: pre_change.get(x) for x in diff_added}
    elif pre_change and not post_change:
        diff_added, diff_removed = None, pre_change
    else:
        diff_added, diff_removed = post_change, None

    return {
        "pre_change": pre_change,
        "post_change": post_change,
        "differences": {
            "added": diff_added,
            "removed": diff_removed,
        },
    }


class ModelInstance:  # pylint: disable=too-many-instance-attributes
    """An individual object to be created or updated as Design Builder iterates through a rendered design YAML file."""

    # Action Definitions
    GET = "get"
    CREATE = "create"
    UPDATE = "update"
    CREATE_OR_UPDATE = "create_or_update"

    ACTION_CHOICES = [GET, CREATE, UPDATE, CREATE_OR_UPDATE]

    # Callback Event types
    PRE_SAVE = "PRE_SAVE"
    POST_SAVE = "POST_SAVE"

    def __init__(
        self,
        creator: "Builder",
        model_class: Type[Model],
        attributes: dict,
        relationship_manager=None,
        parent=None,
        ext_tag=None,
        ext_value=None,
    ):  # pylint:disable=too-many-arguments
        """Constructor for a ModelInstance."""
        self.ext_tag = ext_tag
        self.ext_value = ext_value
        self.creator = creator
        self.model_class = model_class
        self.name = model_class.__name__
        self.instance: Model = None
        # Make a copy of the attributes so the original
        # design attributes are not overwritten
        self.attributes = {**attributes}
        self.parent = parent
        self.deferred = []
        self.deferred_attributes = {}
        self.signals = {
            self.PRE_SAVE: Signal(),
            self.POST_SAVE: Signal(),
        }

        self.filter = {}
        self.action = None
        self.instance_fields = {}
        self._kwargs = {}
        for direction in Relationship.objects.get_for_model(model_class):
            for relationship in direction:
                self.instance_fields[relationship.slug] = field_factory(self, relationship)

        field: DjangoField
        for field in self.model_class._meta.get_fields():
            self.instance_fields[field.name] = field_factory(self, field)

        self.created = False
        self.nautobot_id = None
        self._parse_attributes()
        self.relationship_manager = relationship_manager
        if self.relationship_manager is None:
            self.relationship_manager = self.model_class.objects

        try:
            self._load_instance()
        except ObjectDoesNotExist as ex:
            raise errors.DoesNotExistError(self) from ex
        except MultipleObjectsReturned as ex:
            raise errors.MultipleObjectsReturnedError(self) from ex

    def get_changes(self, pre_change=None):
        """Determine the differences between the original instance and the current.

        This uses `calculate_changes` to determine the change dictionary. See that
        method for details.
        """
        return calculate_changes(
            self.instance,
            initial_state=self._initial_state,
            created=self.created,
            pre_change=pre_change,
        )

    def create_child(
        self,
        model_class: Type[Model],
        attributes: Dict,
        relationship_manager: Manager = None,
    ) -> "ModelInstance":
        """Create a new ModelInstance that is linked to the current instance.

        Args:
            model_class (Type[Model]): Class of the child model.
            attributes (Dict): Design attributes for the child.
            relationship_manager (Manager): Database relationship manager to use for the new instance.

        Returns:
            ModelInstance: Model instance that has its parent correctly set.
        """
        return ModelInstance(
            self.creator,
            model_class,
            attributes,
            relationship_manager,
            parent=self,
        )

    def _parse_attributes(self):  # pylint: disable=too-many-branches
        self.custom_fields = self.attributes.pop("custom_fields", {})
        self.custom_relationships = self.attributes.pop("custom_relationships", {})
        attribute_names = list(self.attributes.keys())
        while attribute_names:
            key = attribute_names.pop(0)
            if key == NAUTOBOT_ID:
                self.nautobot_id = self.attributes[key]
                continue

            self.attributes[key] = self.creator.resolve_values(self.attributes[key])
            if key.startswith("!"):
                value = self.attributes.pop(key)
                args = key.lstrip("!").split(":")

                extn = self.creator.get_extension("attribute", args[0])
                if extn:
                    result = extn.attribute(*args[1:], value=self.creator.resolve_values(value), model_instance=self)
                    if isinstance(result, tuple):
                        self.attributes[result[0]] = result[1]
                    elif isinstance(result, dict):
                        self.attributes.update(result)
                        attribute_names.extend(result.keys())
                    elif result is not None:
                        raise errors.DesignImplementationError(f"Cannot handle extension return type {type(result)}")
                elif args[0] in [self.GET, self.UPDATE, self.CREATE_OR_UPDATE]:
                    self.action = args[0]
                    self.filter[args[1]] = value

                    if self.action is None:
                        self.action = args[0]
                    elif self.action != args[0]:
                        raise errors.DesignImplementationError(
                            f"Can perform only one action for a model, got both {self.action} and {args[0]}",
                            self.model_class,
                        )
                else:
                    raise errors.DesignImplementationError(f"Unknown action {args[0]}", self.model_class)
            elif "__" in key:
                fieldname, search = key.split("__", 1)
                if not hasattr(self.model_class, fieldname):
                    raise errors.DesignImplementationError(f"{fieldname} is not a property", self.model_class)
                self.attributes[fieldname] = {search: self.attributes.pop(key)}
            elif not hasattr(self.model_class, key) and key not in self.instance_fields:
                value = self.creator.resolve_values(self.attributes.pop(key))
                if isinstance(value, ModelInstance):
                    value = value.instance
                self._kwargs[key] = value
                # raise errors.DesignImplementationError(f"{key} is not a property", self.model_class)

        if self.action is None:
            self.action = self.CREATE
        if self.action not in self.ACTION_CHOICES:
            raise errors.DesignImplementationError(f"Unknown action {self.action}", self.model_class)

    def connect(self, signal: Signal, handler: FunctionType):
        """Connect a handler between this model instance (as sender) and signal.

        Args:
            signal (Signal): Signal to listen for.
            handler (FunctionType): Callback function
        """
        self.signals[signal].connect(handler, self)

    def _load_instance(self):  # pylint: disable=too-many-branches
        # If the objects is already an existing Nautobot object, just get it.
        if self.nautobot_id:
            self.created = False
            self.instance = self.model_class.objects.get(id=self.nautobot_id)
            self._initial_state = serialize_object_v2(self.instance)
            return

        query_filter = _map_query_values(self.filter)
        if self.action == self.GET:
            self.instance = self.model_class.objects.get(**query_filter)
            return

        if self.action in [self.UPDATE, self.CREATE_OR_UPDATE]:
            # perform nested lookups. First collect all the
            # query params for top-level relationships, then
            # perform the actual lookup
            for query_param in list(query_filter.keys()):
                if "__" in query_param:
                    value = query_filter.pop(query_param)
                    attribute, filter_param = query_param.split("__", 1)
                    query_filter.setdefault(attribute, {})
                    query_filter[attribute][f"!get:{filter_param}"] = value

            for query_param, value in query_filter.items():
                if isinstance(value, Mapping):
                    rel = getattr(self.model_class, query_param)
                    queryset = rel.get_queryset()
                    model = self.create_child(queryset.model, value, relationship_manager=queryset)
                    if model.action != self.GET:
                        model.save(value)
                    query_filter[query_param] = model.instance

            try:
                self.instance = self.relationship_manager.get(**query_filter)
                self._initial_state = serialize_object_v2(self.instance)
                return
            except ObjectDoesNotExist:
                if self.action == "update":
                    # pylint: disable=raise-missing-from
                    raise errors.DesignImplementationError(f"No match with {query_filter}", self.model_class)
                self.created = True
                # since the object was not found, we need to
                # put the search criteria back into the attributes
                # so that they will be set when the object is created
                self.attributes.update(query_filter)
        elif self.action != "create":
            raise errors.DesignImplementationError(f"Unknown database action {self.action}", self.model_class)

        self._initial_state = {}
        if not self.instance:
            self.created = True
        try:
            self.instance = self.model_class(**self._kwargs)
        except TypeError as ex:
            raise errors.DesignImplementationError(str(ex), self.model_class)

    def _update_fields(self, output_dict):  # pylint: disable=too-many-branches
        if self.action == self.GET and self.attributes:
            raise ValueError("Cannot update fields when using the GET action")

        for field_name, field in self.instance_fields.items():
            if field_name in self.attributes:
                value = self.attributes.pop(field_name)
                if field.deferrable:
                    self.deferred.append(field_name)
                    self.deferred_attributes[field_name] = self.creator.resolve_values(value)
                else:
                    field.set_value(value, output_dict)
            elif (
                hasattr(self.relationship_manager, "field")
                and (isinstance(field, (OneToOneField, ManyToOneField)))
                and self.instance_fields[field_name].field == self.relationship_manager.field
            ):
                field.set_value(self.relationship_manager.instance, output_dict)

        for key, value in self.attributes.items():
            if hasattr(self.instance, key):
                setattr(self.instance, key, value)

        for key, value in self.custom_fields.items():
            self.set_custom_field(key, value)

    def save(self, output_dict):
        """Save the model instance to the database."""
        # The reason we call _update_fields at this point is
        # that some attributes passed into the constructor
        # may not have been saved yet (thus have no ID). By
        # deferring the update until just before save, we can
        # ensure that parent instances have been saved and
        # assigned a primary key
        self._update_fields(output_dict)
        self.signals[ModelInstance.PRE_SAVE].send(sender=self, instance=self)

        msg = "Created" if self.instance._state.adding else "Updated"  # pylint: disable=protected-access
        try:
            self.instance.full_clean()
            self.instance.save()
            if self.parent is None:
                self.creator.log_success(message=f"{msg} {self.name} {self.instance}", obj=self.instance)
            self.creator.journal.log(self)
            self.instance.refresh_from_db()
        except ValidationError as validation_error:
            raise errors.DesignValidationError(self) from validation_error

        for field_name in self.deferred:
            items = self.deferred_attributes[field_name]
            if isinstance(items, dict):
                items = [items]

            for item in items:
                field = self.instance_fields[field_name]
                if isinstance(item, ModelInstance):
                    item_dict = output_dict
                    related_object = item
                    if item.ext_tag:
                        # If the item is a Design Builder extension, we get the ID
                        item_dict[item.ext_tag][NAUTOBOT_ID] = str(item.instance.id)
                else:
                    item_dict = item
                    relationship_manager = None
                    if hasattr(self.instance, field_name):
                        relationship_manager = getattr(self.instance, field_name)
                    related_object = self.create_child(field.model, item, relationship_manager)
                # The item_dict is recursively updated
                related_object.save(item_dict)
                # BEWARE
                # DO NOT REMOVE THE FOLLOWING LINE, IT WILL BREAK THINGS
                # THAT ARE UPDATED VIA SIGNALS, ESPECIALLY CABLES!
                self.instance.refresh_from_db()

                field.set_value(related_object.instance, item_dict)
        self.signals[ModelInstance.POST_SAVE].send(sender=self, instance=self)
        output_dict[NAUTOBOT_ID] = str(self.instance.id)

    def set_custom_field(self, field, value):
        """Sets a value for a custom field."""
        self.instance.cf[field] = value


# Don't add models from these app_labels to the
# object creator's list of top level models
_OBJECT_TYPES_APP_FILTER = set(
    [
        "django_celery_beat",
        "admin",
        "users",
        "django_rq",
        "auth",
        "taggit",
        "database",
        "contenttypes",
        "sessions",
        "social_django",
    ]
)


class Builder(LoggingMixin):
    """Iterates through a design and creates and updates the objects defined within."""

    model_map: Dict[str, Type[Model]]

    def __new__(cls, *args, **kwargs):
        """Sets the model_map class attribute when the first Builder initialized."""
        # only populate the model_map once
        if not hasattr(cls, "model_map"):
            cls.model_map = {}
            for model_class in apps.get_models():
                if model_class._meta.app_label in _OBJECT_TYPES_APP_FILTER:
                    continue
                plural_name = str_to_var_name(model_class._meta.verbose_name_plural)
                cls.model_map[plural_name] = model_class
        return object.__new__(cls)

    def __init__(
        self, job_result: JobResult = None, extensions: List[ext.Extension] = None, journal: models.Journal = None
    ):
        """Constructor for Builder."""
        # builder_output is an auxiliary struct to store the output design with the corresponding Nautobot IDs
        self.builder_output = {}
        self.job_result = job_result

        self.extensions = {
            "extensions": [],
            "attribute": {},
            "value": {},
        }
        if extensions is None:
            extensions = []

        for extn_cls in [*extensions, *ext.extensions()]:
            if not issubclass(extn_cls, ext.Extension):
                raise errors.DesignImplementationError("{extn_cls} is not an action tag extension.")

            extn = {
                "class": extn_cls,
                "object": None,
            }
            if issubclass(extn_cls, ext.AttributeExtension):
                self.extensions["attribute"][extn_cls.tag] = extn
            if issubclass(extn_cls, ext.ValueExtension):
                self.extensions["value"][extn_cls.tag] = extn

            self.extensions["extensions"].append(extn)

        self.journal = Journal(design_journal=journal)

    def decommission_object(self, object_id, object_name):
        """This method decommissions an specific object_id from the design instance."""
        self.journal.design_journal.design_instance.decommission(
            local_logger=get_logger(__name__, self.job_result), object_id=object_id
        )
        self.log_success(
            message=f"Decommissioned {object_name} with ID {object_id} from design instance {self.journal.design_journal.design_instance}."
        )

    def get_extension(self, ext_type: str, tag: str) -> ext.Extension:
        """Looks up an extension based on its tag name and returns an instance of that Extension type.

        Args:
            ext_type (str): the type of the extension, i.e. 'attribute' or 'value'
            tag (str): the tag used for the extension, i.e. 'ref' or 'git_context'

        Returns:
            Extension: An instance of the Extension class
        """
        extn = self.extensions[ext_type].get(tag)
        if extn is None:
            return None

        if extn["object"] is None:
            extn["object"] = extn["class"](self)
        return extn["object"]


    @transaction.atomic
    def implement_design(self, design: Dict, deprecated_design: Dict, commit: bool = False, design_file: str = ""):
        """Iterates through items in the design and creates them.

        This process is wrapped in a transaction. If either commit=False (default) or
        an exception is raised, then the transaction is rolled back and no database
        changes will be present. If commit=True and no exceptions are raised then the
        database state should represent the changes provided in the design.

        Args:
            design (Dict): An iterable mapping of design changes.
            commit (bool): Whether or not to commit the transaction. Defaults to False.

        Raises:
            DesignImplementationError: if the model is not in the model map
        """
        if not design:
            raise errors.DesignImplementationError("Empty design")

        try:
            for key, value in design.items():
                if key in self.model_map and value:
                    self._create_objects(self.model_map[key], value, key, design_file)
                elif key not in self.model_map:
                    raise errors.DesignImplementationError(f"Unknown model key {key} in design")

            for _, value in deprecated_design.items():
                self._deprecate_objects(value)

            if commit:
                self.commit()
            else:
                self.roll_back()
        except Exception as ex:
            self.roll_back()
            raise ex

    def resolve_value(self, value, unwrap_model_instance=False):
        """Resolve a value using extensions, if needed."""
        if isinstance(value, str) and value.startswith("!"):
            (action, arg) = value.lstrip("!").split(":", 1)
            extn = self.get_extension("value", action)
            if extn:
                value = extn.value(arg)
            else:
                raise errors.DesignImplementationError(f"Unknown attribute extension {value}")
        if unwrap_model_instance and isinstance(value, ModelInstance):
            value = value.instance
        return value

    def resolve_values(self, value: Union[list, dict, str], unwrap_model_instances: bool = False) -> Any:
        """Resolve a value, or values, using extensions.

        Args:
            value (Union[list,dict,str]): The value to attempt to resolve.

        Returns:
            Any: The resolved value.
        """
        if isinstance(value, str):
            value = self.resolve_value(value, unwrap_model_instances)
        elif isinstance(value, list):
            # copy the list so we don't change the input
            value = list(value)
            for i, item in enumerate(value):
                value[i] = self.resolve_value(item, unwrap_model_instances)
        elif isinstance(value, dict):
            # copy the dict so we don't change the input
            value = dict(value)
            for k, item in value.items():
                value[k] = self.resolve_value(item, unwrap_model_instances)
        return value

    def _create_objects(self, model_cls, objects, key, design_file):
        if isinstance(objects, dict):
            model = ModelInstance(self, model_cls, objects)
            model.save(self.builder_output[design_file][key])
            # TODO: I feel this is not used at all
            if model.deferred_attributes:
                self.builder_output[design_file][key].update(model.deferred_attributes)
        elif isinstance(objects, list):
            for model_instance in objects:
                model_identifier = get_object_identifier(model_instance)
                future_object = None
                for obj in self.builder_output[design_file][key]:
                    obj_identifier = get_object_identifier(obj)
                    if obj_identifier == model_identifier:
                        future_object = obj
                        break

                if future_object:
                    # Recursive function to update the created Nautobot UUIDs into the final design for future reference
                    model = ModelInstance(self, model_cls, model_instance)
                    model.save(future_object)

                    if model.deferred_attributes:
                        inject_nautobot_uuids(model.deferred_attributes, future_object)

    def _deprecate_objects(self, objects):
        if isinstance(objects, list):
            for obj in objects:
                self.decommission_object(obj[0], obj[1])

    def commit(self):
        """Method to commit all changes to the database."""
        for extn in self.extensions["extensions"]:
            if hasattr(extn["object"], "commit"):
                extn["object"].commit()

    def roll_back(self):
        """Looks for any extensions with a roll back method and executes it.

        Used for for rolling back changes that can't be undone with a database rollback, for example config context files.

        """
        for extn in self.extensions["extensions"]:
            if hasattr(extn["object"], "roll_back"):
                extn["object"].roll_back()
