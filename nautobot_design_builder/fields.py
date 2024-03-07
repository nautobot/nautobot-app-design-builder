"""Model fields."""
from abc import ABC, abstractmethod
from functools import partial
from typing import Mapping, Type, TYPE_CHECKING

from django.db import models as django_models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import fields as ct_fields

from taggit.managers import TaggableManager

from nautobot.extras.choices import RelationshipTypeChoices
from nautobot.extras.models import Relationship, RelationshipAssociation

from nautobot_design_builder.errors import DesignImplementationError

if TYPE_CHECKING:
    from .design import ModelInstance

indent = ""
DEBUG = False
class ObjDetails:
    def __init__(self, obj):
        self.instance = obj
        if hasattr(obj, "instance"):
            self.instance = obj.instance
        try:
            description = str(obj)
            if description.startswith("<class"):
                description = None
        except Exception:
            description = None
        
        self.obj = obj
        self.obj_class = obj.__class__.__name__
        self.obj_id = str(getattr(self.instance, "id", None))
        if hasattr(self.instance, "name"):
            self.name = getattr(self.instance, "name")
        else:
            self.name = None
        self.description = description

    def __str__(self):
        if isinstance(self.instance, django_models.Model):
            string = self.obj_class + " "
            if self.name is not None:
                string += '"' + self.name + '"' + ":"
            elif self.description:
                string += self.description + ":"
            string += self.obj_id
            return string
        elif isinstance(self.instance, dict):
            return str(self.obj)
        return self.description or self.name or self.obj_class

def debug(wrapped):
    def wrapper(self, obj, value, *args, **kwargs):
        obj_details = ObjDetails(obj)
        value_details = ObjDetails(value)
        global indent
        print(indent, self.__class__.__name__, "setting", self.field_name, "on", obj_details, "to", value_details)
        indent += "  "
        wrapped(self, obj, value, *args, **kwargs)
        indent = indent[0:-2]
        print(indent, "Exit", self.__class__.__name__)
    if DEBUG:
        return wrapper
    return wrapped

class ModelField(ABC):
    """This represents any type of field (attribute or relationship) on a Nautobot model.
    
    The design builder fields are descriptors that are used to build the
    correct relationship hierarchy of django models based on the design input.
    The fields are used to sequence saves and value assignments in the correct
    order.
    """

    def __set_name__(self, owner, name):
        self.field_name = name

    def __get__(self, obj, objtype=None):
        if obj is None or obj.instance is None:
            return self
        return getattr(obj.instance, self.field_name)

    @abstractmethod
    def __set__(self, obj: "ModelInstance", value):
        """Method used to set the value of the field.

        Args:
            value (Any): Value that should be set on the model field.
        """


class BaseModelField(ModelField):
    """BaseModelFields are backed by django.db.models.fields.Field."""

    field: django_models.Field
    related_model: Type[object]

    def __init__(self, model_class, field: django_models.Field):
        """Create a base model field.

        Args:
            model_instance (ModelInstance): Model instance which this field belongs to.
            field (DjangoField): Database field to be managed.
        """
        self.model_class = model_class
        self.field = field
        self.field_name = field.name
        self.related_model = field.related_model


class SimpleField(BaseModelField):
    """A field that accepts a scalar value."""

    @debug
    def __set__(self, obj: "ModelInstance", value):  # noqa:D102
        setattr(obj.instance, self.field_name, value)


class RelationshipField(BaseModelField):
    """Field that represents a relationship to another model."""

    def _get_instance(self, obj:"ModelInstance", value, relationship_manager=None):
        if isinstance(value, Mapping):
            value = obj.create_child(self.related_model, value, relationship_manager)
        return value


class ForeignKeyField(RelationshipField):
    """One to one relationship field."""

    @debug
    def __set__(self, obj: "ModelInstance", value):  # noqa:D102
        @debug
        def setter(self, obj:"ModelInstance", value:"ModelInstance", save=False):
            value = self._get_instance(obj, value)
            if value._created:
                value.save()
            value: django_models.Model = value.instance
            setattr(obj.instance, self.field_name, value)
            if save:
                obj.instance.save(update_fields=[self.field_name])

        if getattr(value, "deferred", False):
            obj.connect(obj.POST_INSTANCE_SAVE, partial(setter, self, obj, value, True))
        else:
            setter(self, obj, value)

class RelatedForeignKeyField(RelationshipField):
    """One to one relationship field."""

    @debug
    def __set__(self, obj:"ModelInstance", values):  # noqa:D102
        @debug
        def setter(self, obj:"ModelInstance", value):
            value = self._get_instance(obj, value, getattr(obj, self.field_name))
            setattr(value.instance, self.field.field.name, obj.instance)
            value.save()

        for value in values:
            obj.connect(obj.POST_INSTANCE_SAVE, partial(setter, self, obj, value))

class ManyToManyField(RelationshipField):
    """Many to many relationship field."""

    def __init__(self, model_class, field: django_models.Field):  # noqa:D102
        super().__init__(model_class, field)
        if hasattr(field.remote_field, "through"):
            through = field.remote_field.through
            if not through._meta.auto_created:
                self.related_model = through

    @debug
    def __set__(self, obj:"ModelInstance", values):  # noqa:D102
        @debug
        def setter(self, obj:"ModelInstance", value):
            value = self._get_instance(obj, value, getattr(obj.instance, self.field_name))
            if value._created:
                value.save()
            getattr(obj.instance, self.field_name).add(value.instance)

        for value in values:
            obj.connect(obj.POST_INSTANCE_SAVE, partial(setter, self, obj, value))


class RelatedManyToManyField(RelationshipField):
    """Many to many relationship field."""

    def __init__(self, model_class, field: django_models.Field):  # noqa:D102
        super().__init__(model_class, field)
        if hasattr(field.remote_field, "through"):
            through = field.remote_field.through
            if not through._meta.auto_created:
                self.related_model = through

    @debug
    def __set__(self, obj:"ModelInstance", value):  # noqa:D102
        @debug
        def setter(self, obj:"ModelInstance", value):
            # TODO: should this be reversed based on how ManyToManyField works?
            #       if not, can this class be eliminated completely?
            getattr(obj.instance, self.field_name).add(value)
        obj.connect(obj.POST_INSTANCE_SAVE, partial(setter, self, obj, value))


class GenericRelationField(RelationshipField):
    """Generic relationship field."""

    @debug
    def __set__(self, obj:"ModelInstance", values):  # noqa:D102
        if not isinstance(values, list):
            values = [values]
        for value in values:
            value = self._get_instance(obj, value)
            if value._created:
                value.save()
            getattr(obj.instance, self.field_name).add(value.instance)

class GenericForeignKeyField(RelationshipField):
    """Generic foreign key field."""

    @debug
    def __set__(self, obj:"ModelInstance", value):  # noqa:D102
        fk_field = self.field.fk_field
        ct_field = self.field.ct_field
        setattr(obj.instance, fk_field, value.instance.pk)
        setattr(obj.instance, ct_field, ContentType.objects.get_for_model(value.instance))

class TagField(ManyToManyField):
    """Taggit field."""

    def __init__(self, model_instance, field: django_models.Field):  # noqa:D102
        super().__init__(model_instance, field)
        self.related_model = field.remote_field.model


class GenericRelField(RelationshipField):
    """Field used as part of content-types generic relation."""

    @debug
    def __set__(self, obj:"ModelInstance", value):  # noqa:D102
        setattr(obj.instance, self.field.attname, self._get_instance(obj, value))


class CustomRelationshipField(RelationshipField):  # pylint: disable=too-few-public-methods
    """This class models a Nautobot custom relationship."""

    def __init__(self, model_class, relationship: Relationship):
        """Create a new custom relationship field.

        Args:
            relationship (Relationship): The Nautobot custom relationship backing this field.
            model_class (Model): Model class for the remote end of this relationship.
            model_instance (ModelInstance): Object being updated to include this field.
        """
        self.relationship = relationship
        self.field_name = relationship.slug
        self.model_class = model_class
        self.one_to_one = relationship.type == RelationshipTypeChoices.TYPE_ONE_TO_ONE
        self.many_to_one = relationship.type == RelationshipTypeChoices.TYPE_ONE_TO_MANY
        self.one_to_many = self.many_to_one
        self.many_to_many = relationship.type == RelationshipTypeChoices.TYPE_MANY_TO_MANY
        if self.relationship.source_type == ContentType.objects.get_for_model(model_class.model_class):
            self.related_model = relationship.destination_type.model_class()
        else:
            self.related_model = relationship.source_type.model_class()

    @debug
    def __set__(self, obj:"ModelInstance", values):  # noqa:D102
        """Add an association between the created object and the given value.

        Args:
            value (Model): The related object to add.
        """
        def setter(self, obj:"ModelInstance", value):
            value = self._get_instance(obj, value)
            if value._created:
                value.save()

            source = obj.instance
            destination = value.instance
            if self.relationship.source_type == ContentType.objects.get_for_model(destination):
                source, destination = destination, source

            source_type = ContentType.objects.get_for_model(source)
            destination_type = ContentType.objects.get_for_model(destination)
            RelationshipAssociation.objects.update_or_create(
                relationship=self.relationship,
                source_id=source.id,
                source_type=source_type,
                destination_id=destination.id,
                destination_type=destination_type,
            )
        for value in values:
            obj.connect(obj.POST_INSTANCE_SAVE, partial(setter, self, obj, value))


def field_factory(arg1, arg2) -> ModelField:
    """Factory function to create a ModelField."""
    if isinstance(arg2, Relationship):
        return CustomRelationshipField(arg1, arg2)

    field = None
    if not arg2.is_relation:
        field = SimpleField(arg1, arg2)
    elif isinstance(arg2, ct_fields.GenericRelation):
        field = GenericRelationField(arg1, arg2)
    elif isinstance(arg2, ct_fields.GenericRel):
        field = GenericRelField(arg1, arg2)
    elif isinstance(arg2, ct_fields.GenericForeignKey):
        field = GenericForeignKeyField(arg1, arg2)
    elif isinstance(arg2, TaggableManager):
        field = TagField(arg1, arg2)
    elif isinstance(arg2, django_models.ForeignKey):
        field = ForeignKeyField(arg1, arg2)
    elif isinstance(arg2, django_models.ManyToOneRel):
        field = RelatedForeignKeyField(arg1, arg2)
    elif isinstance(arg2, django_models.ManyToManyField):
        field = ManyToManyField(arg1, arg2)
    elif isinstance(arg2, django_models.ManyToManyRel):
        field = RelatedManyToManyField(arg1, arg2)
    else:
        raise DesignImplementationError(f"Cannot manufacture field for {type(arg2)}, {arg2} {arg2.is_relation}")
    return field
