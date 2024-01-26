"""Provides ORM interaction for design builder."""
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

from nautobot_design_builder import errors
from nautobot_design_builder import ext
from nautobot_design_builder.logging import LoggingMixin
from nautobot_design_builder.fields import field_factory, OneToOneField, ManyToOneField


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

    def __init__(self):
        """Constructor for Journal object."""
        self.index = set()
        self.created = {}
        self.updated = {}

    def log(self, model: "ModelInstance"):
        """Log that a model has been created or updated.

        Args:
            model (BaseModel): The model that has been created or updated
        """
        instance = model.instance
        model_type = instance.__class__
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
    ):  # pylint:disable=too-many-arguments
        """Constructor for a ModelInstance."""
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

    def _load_instance(self):
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
                        model.save()
                    query_filter[query_param] = model.instance

            try:
                self.instance = self.relationship_manager.get(**query_filter)
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
        try:
            self.instance = self.model_class(**self._kwargs)
        except TypeError as ex:
            raise errors.DesignImplementationError(str(ex), self.model_class)

    def _update_fields(self):  # pylint: disable=too-many-branches
        if self.action == self.GET and self.attributes:
            raise ValueError("Cannot update fields when using the GET action")

        for field_name, field in self.instance_fields.items():
            if field_name in self.attributes:
                value = self.attributes.pop(field_name)
                if field.deferrable:
                    self.deferred.append(field_name)
                    self.deferred_attributes[field_name] = self.creator.resolve_values(value)
                else:
                    field.set_value(value)
            elif (
                hasattr(self.relationship_manager, "field")
                and (isinstance(field, (OneToOneField, ManyToOneField)))
                and self.instance_fields[field_name].field == self.relationship_manager.field
            ):
                field.set_value(self.relationship_manager.instance)

        for key, value in self.attributes.items():
            if hasattr(self.instance, key):
                setattr(self.instance, key, value)

        for key, value in self.custom_fields.items():
            self.set_custom_field(key, value)

    def save(self):
        """Save the model instance to the database."""
        # The reason we call _update_fields at this point is
        # that some attributes passed into the constructor
        # may not have been saved yet (thus have no ID). By
        # deferring the update until just before save, we can
        # ensure that parent instances have been saved and
        # assigned a primary key
        self._update_fields()
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
                    related_object = item
                else:
                    relationship_manager = None
                    if hasattr(self.instance, field_name):
                        relationship_manager = getattr(self.instance, field_name)
                    related_object = self.create_child(field.model, item, relationship_manager)
                related_object.save()
                # BEWARE
                # DO NOT REMOVE THE FOLLOWING LINE, IT WILL BREAK THINGS
                # THAT ARE UPDATED VIA SIGNALS, ESPECIALLY CABLES!
                self.instance.refresh_from_db()

                field.set_value(related_object.instance)
        self.signals[ModelInstance.POST_SAVE].send(sender=self, instance=self)

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

    def __init__(self, job_result: JobResult = None, extensions: List[ext.Extension] = None):
        """Constructor for Builder."""
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

        self.journal = Journal()

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
    def implement_design(self, design: Dict, commit: bool = False):
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
                    self._create_objects(self.model_map[key], value)
                else:
                    raise errors.DesignImplementationError(f"Unknown model key {key} in design")
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

    def _create_objects(self, model_cls, objects):
        if isinstance(objects, dict):
            model = ModelInstance(self, model_cls, objects)
            model.save()
        elif isinstance(objects, list):
            for model_instance in objects:
                model = ModelInstance(self, model_cls, model_instance)
                model.save()

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
