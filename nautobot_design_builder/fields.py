"""Model fields."""
from abc import ABC, abstractmethod
from typing import Mapping, Type

from django.db import models as django_models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import fields as ct_fields

from taggit.managers import TaggableManager

from nautobot.extras.choices import RelationshipTypeChoices
from nautobot.extras.models import Relationship, RelationshipAssociation

from nautobot_design_builder.errors import DesignImplementationError


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
    def __set__(self, obj, value):
        """Method used to set the value of the field.

        Args:
            value (Any): Value that should be set on the model field.
        """

    @property
    @abstractmethod
    def deferrable(self):
        """Determine whether the saving of this field should be deferred."""


class BaseModelField(ModelField):
    """BaseModelFields are backed by django.db.models.fields.Field."""

    field: django_models.Field
    related_model: Type[object]
    deferrable = False

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

    def __set__(self, obj, value):  # noqa:D102
        setattr(obj.instance, self.field_name, value)


class RelationshipField(BaseModelField):
    """Field that represents a relationship to another model."""
    deferrable = True

    def _get_instance(self, obj, value):
        if isinstance(value, Mapping):
            value = obj.create_child(self.related_model, value)
            if value._created:
                value.save()
            value = value.instance
        if hasattr(value, "instance"):
            value = value.instance
        elif value is not None and not isinstance(value, django_models.Model):
            raise DesignImplementationError(
                f"Expecting input field '{self.field.name}' to be a mapping or reference, got {type(value)}: {value}"
            )
        return value


class ForeignKeyField(RelationshipField):
    """One to one relationship field."""

    @property
    def deferrable(self):
        return self.field.null and self.field.blank

    def __set__(self, obj, value):  # noqa:D102
        setattr(obj.instance, self.field_name, self._get_instance(obj, value))
        if self.deferrable:
            obj.instance.save()

class RelatedForeignKeyField(RelationshipField):
    """One to one relationship field."""

    def __set__(self, obj, value):  # noqa:D102
        if hasattr(value, "instance"):
            value = value.instance
        elif not isinstance(value, (type(None), django_models.Model)):
            raise DesignImplementationError(
                f"Expecting input field '{self.field.name}' to be a mapping or reference, got {type(value)}: {value}"
            )

        setattr(value, self.field.field.name, obj.instance)
        value.save()


class ManyToManyField(RelationshipField):
    """Many to many relationship field."""

    def __init__(self, model_class, field: django_models.Field):  # noqa:D102
        super().__init__(model_class, field)
        if hasattr(field.remote_field, "through"):
            through = field.remote_field.through
            if not through._meta.auto_created:
                self.related_model = through

    def __set__(self, obj, value):  # noqa:D102
        getattr(obj.instance, self.field_name).add(value)


class RelatedManyToManyField(RelationshipField):
    """Many to many relationship field."""

    def __init__(self, model_class, field: django_models.Field):  # noqa:D102
        super().__init__(model_class, field)
        if hasattr(field.remote_field, "through"):
            through = field.remote_field.through
            if not through._meta.auto_created:
                self.related_model = through

    def __set__(self, obj, value):  # noqa:D102
        getattr(obj.instance, self.field_name).add(value)


class GenericRelationField(RelationshipField):
    """Generic relationship field."""

    deferrable = False

    def __set__(self, obj, values):  # noqa:D102
        if not isinstance(values, list):
            values = [values]
        for value in values:
            getattr(obj.instance, self.field_name).add(self._get_instance(obj, value))

class GenericForeignKeyField(RelationshipField):
    """Generic foreign key field."""

    deferrable = False

    def __set__(self, obj, value):  # noqa:D102
        fk_field = self.field.fk_field
        ct_field = self.field.ct_field
        if hasattr(value, "instance"):
            value = value.instance
        setattr(obj.instance, fk_field, value.pk)
        setattr(obj.instance, ct_field, ContentType.objects.get_for_model(value))

class TagField(ManyToManyField):
    """Taggit field."""

    def __init__(self, model_instance, field: django_models.Field):  # noqa:D102
        super().__init__(model_instance, field)
        self.related_model = field.remote_field.model


class GenericRelField(RelationshipField):
    """Field used as part of content-types generic relation."""

    deferrable = False

    def __set__(self, obj, value):  # noqa:D102
        setattr(obj.instance, self.field.attname, self._get_instance(obj, value))


class CustomRelationshipField(ModelField):  # pylint: disable=too-few-public-methods
    """This class models a Nautobot custom relationship."""

    deferrable = True

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

    def __set__(self, obj, value):  # noqa:D102
        """Add an association between the created object and the given value.

        Args:
            value (Model): The related object to add.
        """
        source = obj.instance
        destination = value
        if self.relationship.source_type == ContentType.objects.get_for_model(value):
            source = value
            destination = obj.instance

        source_type = ContentType.objects.get_for_model(source)
        destination_type = ContentType.objects.get_for_model(destination)
        RelationshipAssociation.objects.update_or_create(
            relationship=self.relationship,
            source_id=source.id,
            source_type=source_type,
            destination_id=destination.id,
            destination_type=destination_type,
        )


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
