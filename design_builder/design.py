"""Provides ORM interaction for design builder."""
from typing import Dict, List, Mapping, Type, Union, overload

from django.apps import apps
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError
from django.db import transaction

from nautobot.core.graphql.utils import str_to_var_name
from nautobot.core.models import BaseModel
from nautobot.extras.choices import RelationshipTypeChoices
from nautobot.extras.models import JobResult, Relationship, RelationshipAssociation

from design_builder.errors import DesignImplementationError, DesignValidationError
from design_builder.ext import GitContextExtension, ReferenceExtension
from design_builder.logging import LoggingMixin


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


class CustomRelationshipField:  # pylint: disable=too-few-public-methods
    """This class models a Nautobot custom relationship."""

    def __init__(self, relationship: Relationship, model_class: BaseModel, creator_object: "ModelInstance"):
        """Create a new custom relationship field.

        Args:
            relationship (Relationship): The Nautobot custom relationship backing this field.
            model_class (BaseModel): Model class for the remote end of this relationship.
            creator_object (CreatorObject): Object being updated to include this field.
        """
        self.relationship = relationship
        self.creator_object = creator_object
        self.one_to_one = relationship.type == RelationshipTypeChoices.TYPE_ONE_TO_ONE
        self.many_to_one = relationship.type == RelationshipTypeChoices.TYPE_ONE_TO_MANY
        self.one_to_many = self.many_to_one
        self.many_to_many = relationship.type == RelationshipTypeChoices.TYPE_MANY_TO_MANY
        if self.relationship.source_type == ContentType.objects.get_for_model(model_class):
            self.related_model = relationship.destination_type.model_class()
        else:
            self.related_model = relationship.source_type.model_class()

    def add(self, value: BaseModel):
        """Add an association between the created object and the given value.

        Args:
            value (BaseModel): The related object to add.
        """
        source = self.creator_object.instance
        destination = value
        if self.relationship.source_type == ContentType.objects.get_for_model(value):
            source = value
            destination = self.creator_object.instance

        source_type = ContentType.objects.get_for_model(source)
        destination_type = ContentType.objects.get_for_model(destination)
        RelationshipAssociation.objects.update_or_create(
            relationship=self.relationship,
            source_id=source.id,
            source_type=source_type,
            destination_id=destination.id,
            destination_type=destination_type,
        )


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
        # Make a copy of the attributes so the original
        # design attributes are not overwritten
        self.attributes = {**attributes}

        self.filter = {}
        self.action = None
        self.instance_fields = {}
        for direction in Relationship.objects.get_for_model(model_class):
            for relationship in direction:
                self.instance_fields[relationship.slug] = CustomRelationshipField(relationship, self.model_class, self)

        self._parse_attributes()

        self.relationship_manager = relationship_manager
        self.instance: BaseModel = None
        self._load_instance()

        self.model_fields = {field.name: field for field in model_class._meta.get_fields()}
        for field in self.instance._meta.get_fields():
            self.instance_fields[field.name] = field

        self._update_fields()

    def _parse_attributes(self):  # pylint: disable=too-many-branches
        self.custom_fields = self.attributes.pop("custom_fields", {})
        self.custom_relationships = self.attributes.pop("custom_relationships", {})
        for key in list(self.attributes.keys()):
            if key.startswith("!"):
                args = key.lstrip("!").split(":", 1)

                extn = self.creator.get_extension("attribute", args[0])
                if extn:
                    result = extn.attribute(*args[1:], value=self.attributes.pop(key), creator_object=self)
                    if result:
                        self.attributes[result[0]] = result[1]
                elif args[0] in [self.GET, self.UPDATE, self.CREATE_OR_UPDATE]:
                    self.action = args[0]
                    self.filter[args[1]] = self.attributes.pop(key)
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
        query_filter = self.creator.map_values(self.filter)
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

        deferred = []
        deferred_attributes = {}

        for field_name, field in self.instance_fields.items():
            if isinstance(field, CustomRelationshipField) and field_name in self.attributes:
                deferred.append(field_name)
                deferred_attributes[field_name] = self.attributes.pop(field_name)
            elif field.many_to_one and field_name in self.attributes:
                kwargs = self.attributes.pop(field_name)
                if isinstance(kwargs, Mapping):
                    self.attributes[field_name] = self.creator._get(  # pylint: disable=protected-access
                        self.instance_fields[field_name].related_model, kwargs
                    )
                elif isinstance(kwargs, str) and kwargs.startswith("!"):
                    (action, arg) = kwargs.lstrip("!").split(":", 1)
                    extn = self.creator.get_extension("value", action)
                    if extn:
                        self.attributes[field_name] = extn.value(arg).instance
                    else:
                        raise DesignImplementationError(f"Unknown value extension {action}")
                else:
                    raise DesignImplementationError(
                        f"Expecting input field '{field} to be a mapping or reference, got {type(kwargs)}: {kwargs}"
                    )
            elif (
                (self.relationship_manager and hasattr(self.relationship_manager, "field"))
                and (field.one_to_one or field.many_to_one)
                and self.model_fields[field_name] == self.relationship_manager.field
            ):
                setattr(self.instance, field_name, self.relationship_manager.instance)
            elif field.one_to_one or field.one_to_many or field.many_to_many:
                if field_name in self.attributes:
                    deferred.append(field_name)
                    deferred_attributes[field_name] = self.attributes.pop(field_name)

        for key, value in self.attributes.items():
            self.set_field(key, value)

        for key, value in self.custom_fields.items():
            self.set_custom_field(key, value)

        self.creator.save_model(self)

        for field in deferred:
            items = deferred_attributes[field]
            if isinstance(items, dict):
                items = [items]

            for item in items:
                if isinstance(item, str) and item.startswith("!"):
                    action, arg = item.lstrip("!").split(":", 1)
                    extn = self.creator.get_extension("value", action)
                    if extn:
                        self.create_or_update_related(field, item, related_object=extn.value(arg))
                    else:
                        raise DesignImplementationError(f"Unknown value extension {action}")
                else:
                    self.create_or_update_related(field, item)

    def create_or_update_related(self, field_name, attributes, related_object=None):
        """Creates or updates a relationship between ORM objects.

        Args:
            field_name (str): The field name of the object to update, i.e. 'platform'
            attributes: the attribute of the related object to update, i.e. 'name', 'model'

        Raises:
            DesignImplementationError: If the relationship type is not valid
        """
        field = self.instance_fields[field_name]
        relationship_manager = None
        if hasattr(self.instance, field_name):
            relationship_manager = getattr(self.instance, field_name)

        if related_object is None:
            related_object = ModelInstance(self.creator, field.related_model, attributes, relationship_manager)
            if isinstance(field, GenericRelation):
                setattr(related_object, "content_object", self.instance)
            elif not isinstance(field, CustomRelationshipField):
                setattr(related_object, field.remote_field.name, self.instance)

        related_instance = related_object
        if isinstance(related_instance, ModelInstance):
            related_instance = related_instance.instance

        if isinstance(field, CustomRelationshipField):
            field.add(related_instance)
        elif field.one_to_one:
            self.set_field(field_name, related_instance)
            self.instance.validated_save()
        elif field.one_to_many:
            getattr(self.instance, field_name).add(related_instance, bulk=False)
        elif field.many_to_many:
            getattr(self.instance, field_name).add(related_instance)
        else:
            raise DesignImplementationError("Can't handle relationship type", self.instance)

    def set_field(self, field, value):
        """Sets a value for a field."""
        if isinstance(self.instance_fields.get(field, None), CustomRelationshipField):
            self.instance_fields[field].set(value)
        else:
            setattr(self.instance, field, value)

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

    def __init__(self, job_result: JobResult = None):
        """Constructor for Builder."""
        self.job_result = job_result

        self.extensions = {
            "extensions": [],
            "attribute": {},
            "value": {},
        }

        for extn_cls in [ReferenceExtension, GitContextExtension]:
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

    @overload
    def map_values(self, mapping_or_str: Mapping) -> Mapping:
        ...

    @overload
    def map_values(self, mapping_or_str: str) -> str:
        ...

    def map_values(self, mapping_or_primitive: Union[Mapping, str]) -> Union[Mapping, str]:
        """Map a set of values to their actual values.

        This method will look for any values that can be resolved
        using extensions and will perform the extension lookup. The returned
        value will be either a Mapping or a string, depending on the input.

        Args:
            mapping_or_str (Union[Mapping,str]): Input to map with extensions

        Raises:
            DesignImplementationError: If the input type is not a string or mapping or if
                an extension cannot be resolved.

        Returns:
            Union[Mapping,str]: The resolved value(s)
        """
        retval = mapping_or_primitive
        if isinstance(mapping_or_primitive, Mapping):
            retval = {}
            for key, value in mapping_or_primitive.items():
                retval[key] = self.map_values(value)
        elif isinstance(mapping_or_primitive, str) and mapping_or_primitive.startswith("!"):
            (action, arg) = mapping_or_primitive.lstrip("!").split(":", 1)
            extn = self.get_extension("value", action)
            if extn:
                retval = extn.value(arg)
            else:
                raise DesignImplementationError(f"Unknown value extension {action}")
        return retval

    def _create_objects(self, model_cls, objects):
        if isinstance(objects, dict):
            ModelInstance(self, model_cls, objects)
        elif isinstance(objects, list):
            for creator_object in objects:
                ModelInstance(self, model_cls, creator_object)

    def _get(self, model_cls: Type[BaseModel], lookup: dict):
        objects = model_cls.objects
        try:
            return objects.get(**self.map_values(lookup))  # pylint: disable=not-a-mapping
        except MultipleObjectsReturned:
            raise DesignImplementationError(
                "Expected exactly 1 object for {model_cls.__name__}({lookup}) but got more than one"
            )
        except ObjectDoesNotExist:
            query = ",".join([f'{k}="{v}"' for k, v in lookup.items()])
            raise DesignImplementationError(f"Could not find {model_cls.__name__}: {query}")

    def save_model(self, model):
        """Performs a validated save on the object and then refreshes that object from the database.

        Args:
            model (CreatorObject): ingests the creator property of a CreatorObject model

        Raises:
            DesignValidationError: if the model fails to save, refresh or log to the journal
        """
        created = model.instance._state.adding  # pylint: disable=protected-access
        msg = "Created" if model.instance._state.adding else "Updated"  # pylint: disable=protected-access
        fail_msg = "create" if model.instance._state.adding else "update"  # pylint: disable=protected-access
        try:
            model.instance.full_clean()
            model.instance.save()
            self.log_success(message=f"{msg} {model.name} {model.instance}", obj=model.instance)
            model.instance.refresh_from_db()
            self.journal.log(model, created)
        except ValidationError as validation_error:
            self.log_failure(message=f"Failed to {fail_msg} {model.name} {model.instance}")
            raise DesignValidationError(f"{model.instance} failed validation: {validation_error}")

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
