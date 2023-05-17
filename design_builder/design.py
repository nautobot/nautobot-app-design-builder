"""Provides ORM interaction for design builder."""
from typing import Dict, List, Mapping, Type

from django.apps import apps
from django.db.models.fields import Field as DjangoField
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction


from nautobot.core.graphql.utils import str_to_var_name
from nautobot.core.models import BaseModel
from nautobot.extras.models import JobResult, Relationship

from design_builder.errors import DesignImplementationError, DesignValidationError
from design_builder import ext
from design_builder.logging import LoggingMixin
from design_builder.fields import field_factory, OneToOneField, ManyToOneField


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

    def log(self, model: BaseModel, created=False):
        """Log that a model has been created or updated.

        Args:
            model (BaseModel): The model that has been created or updated
            created (bool, optional): If the object has just been created
            then this argument should be True. Defaults to False.
        """
        instance = model.instance
        model_type = instance.__class__
        if instance.pk not in self.index:
            self.index.add(instance.pk)

            if created:
                index = self.created
            else:
                index = self.updated

            index.setdefault(model_type, set())
            index[model_type].add(instance.pk)

    @property
    def created_objects(self) -> List[BaseModel]:
        """Return a list of Nautobot objects that were created.

        Returns:
            List[BaseModel]: All of the objects that were created during the
            design implementation.
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

    GET = "get"
    CREATE = "create"
    UPDATE = "update"
    CREATE_OR_UPDATE = "create_or_update"

    ACTION_CHOICES = [GET, CREATE, UPDATE, CREATE_OR_UPDATE]

    def __init__(self, creator: "Builder", model_class: Type[BaseModel], attributes: dict, relationship_manager=None):
        """Constructor for a ModelInstance."""
        self.creator = creator
        self.model_class = model_class
        self.name = model_class.__name__
        self.instance: BaseModel = None
        # Make a copy of the attributes so the original
        # design attributes are not overwritten
        self.attributes = {**attributes}
        self.deferred = []
        self.deferred_attributes = {}

        self.filter = {}
        self.action = None
        self.instance_fields = {}
        for direction in Relationship.objects.get_for_model(model_class):
            for relationship in direction:
                self.instance_fields[relationship.slug] = field_factory(self, relationship)

        field: DjangoField
        for field in self.model_class._meta.get_fields():
            self.instance_fields[field.name] = field_factory(self, field)

        self._parse_attributes()
        self.relationship_manager = relationship_manager
        self._load_instance()

    def _parse_attributes(self):  # pylint: disable=too-many-branches
        self.custom_fields = self.attributes.pop("custom_fields", {})
        self.custom_relationships = self.attributes.pop("custom_relationships", {})
        for key in list(self.attributes.keys()):
            self.attributes[key] = self.creator.resolve_values(self.attributes[key])
            if key.startswith("!"):
                value = self.attributes.pop(key)
                args = key.lstrip("!").split(":")

                extn = self.creator.get_extension("attribute", args[0])
                if extn:
                    result = extn.attribute(*args[1:], value=value, model_instance=self)
                    if result:
                        self.attributes[result[0]] = result[1]
                elif args[0] in [self.GET, self.UPDATE, self.CREATE_OR_UPDATE]:
                    self.action = args[0]
                    self.filter[args[1]] = value
                    if self.action is None:
                        self.action = args[0]
                    elif self.action != args[0]:
                        raise DesignImplementationError(
                            f"Can perform only one action for a model, got both {self.action} and {args[0]}",
                            self.model_class,
                        )
                else:
                    raise DesignImplementationError(f"Unknown action {args[0]}", self.model_class)
            elif "__" in key:
                fieldname, search = key.split("__", 1)
                if not hasattr(self.model_class, fieldname):
                    raise DesignImplementationError(f"{fieldname} is not a property", self.model_class)
                self.attributes[fieldname] = {search: self.attributes.pop(key)}
            elif not hasattr(self.model_class, key) and key not in self.instance_fields:
                raise DesignImplementationError(f"{key} is not a property", self.model_class)

        if self.action is None:
            self.action = self.CREATE
        if self.action not in self.ACTION_CHOICES:
            raise DesignImplementationError(f"Unknown action {self.action}", self.model_class)

    def _load_instance(self):
        query_filter = _map_query_values(self.filter)
        if self.action == self.GET:
            self.instance = self.model_class.objects.get(**query_filter)
            return

        if self.action in [self.UPDATE, self.CREATE_OR_UPDATE]:
            try:
                if self.relationship_manager is None:
                    self.instance = self.model_class.objects.get(**query_filter)
                else:
                    self.instance = self.relationship_manager.get(**query_filter)
                return
            except ObjectDoesNotExist:
                if self.action == "update":
                    raise DesignImplementationError(f"No match with {query_filter}", self.model_class)
                # since the object was not found, we need to
                # put the search criteria back into the attributes
                # so that they will be set when the object is created
                self.attributes.update(query_filter)
        elif self.action != "create":
            raise DesignImplementationError(f"Unknown database action {self.action}", self.model_class)
        self.instance = self.model_class()

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
        self.instance.full_clean()
        self.instance.save()
        self.instance.refresh_from_db()

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
                    related_object = ModelInstance(self.creator, field.model, item, relationship_manager)
                related_object.save()
                field.set_value(related_object.instance)

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

    model_map: Dict[str, Type[BaseModel]]

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
                raise DesignImplementationError("{extn_cls} is not an action tag extension.")

            extn = {
                "class": extn_cls,
                "object": None,
            }
            self.extensions["extensions"].append(extn)
            for ext_type in ["attribute", "value"]:
                for extn in self.extensions["extensions"]:
                    if hasattr(extn_cls, f"{ext_type}_tag"):
                        self.extensions[ext_type][getattr(extn_cls, f"{ext_type}_tag")] = extn

        self.journal = Journal()

    def get_extension(self, ext_type, tag):
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
    def implement_design(self, design, commit=False):
        """Iterates through items in the design and creates them.

        This process is wrapped in a transaction. If either commit=False (default) or
        an exception is raised, then the transaction is rolled back and no database
        changes will be present. If commit=True and no exceptions are raised then the
        database state should represent the changes provided in the design.

        Args:
            design: An iterable mapping of design changes.
            commit: Whether or not to commit the transaction. Defaults to False.

        Raises:
            DesignImplementationError: if the model is not in the model map
        """
        sid = transaction.savepoint()
        try:
            for key, value in design.items():
                if key in self.model_map and value:
                    self._create_objects(self.model_map[key], value)
                else:
                    raise DesignImplementationError(f"Unknown model key {key} in design")
            if not commit:
                transaction.savepoint_rollback(sid)
                self.roll_back()
        except Exception as ex:
            self.roll_back()
            raise ex

    def resolve_value(self, value):
        """Resolve a value using extensions, if needed."""
        if isinstance(value, str) and value.startswith("!"):
            (action, arg) = value.lstrip("!").split(":", 1)
            extn = self.get_extension("value", action)
            if extn:
                value = extn.value(arg)
            else:
                raise DesignImplementationError(f"Unknown attribute extension {value}")
        return value

    def resolve_values(self, value):
        """Resolve a value, or values, using extensions.

        Args:
            value (Union[list,dict,str]): The value to attempt to resolve.

        Returns:
            Any: The resolved value.
        """
        if isinstance(value, str):
            value = self.resolve_value(value)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                value[i] = self.resolve_value(item)
        elif isinstance(value, dict):
            for k, item in value.items():
                value[k] = self.resolve_value(item)
        return value

    def _create_objects(self, model_cls, objects):
        if isinstance(objects, dict):
            model = ModelInstance(self, model_cls, objects)
            self.save_model(model)
        elif isinstance(objects, list):
            for model_instance in objects:
                model = ModelInstance(self, model_cls, model_instance)
                self.save_model(model)

    def save_model(self, model):
        """Performs a validated save on the object and then refreshes that object from the database.

        Args:
            model (CreatorObject): ingests the creator property of a CreatorObject model

        Raises:
            DesignValidationError: if the model fails to save, refresh or log to the journal
        """
        created = model.instance._state.adding  # pylint: disable=protected-access
        msg = "Created" if model.instance._state.adding else "Updated"  # pylint: disable=protected-access
        try:
            model.save()
            self.log_success(message=f"{msg} {model.name} {model.instance}", obj=model.instance)
            self.journal.log(model, created)
        except ValidationError as validation_error:
            instance_str = str(model.instance)
            type_str = model.model_class._meta.verbose_name.capitalize()
            if instance_str:
                type_str = f"{type_str} {instance_str}"
            raise DesignValidationError(f"{type_str} failed validation") from validation_error

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
