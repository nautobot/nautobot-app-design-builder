"""Model fields."""
from abc import ABC, abstractmethod
from typing import Mapping, Type

from django.db.models import Model
from django.db.models.fields import Field as DjangoField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from taggit.managers import TaggableManager

from nautobot.extras.choices import RelationshipTypeChoices
from nautobot.extras.models import Relationship, RelationshipAssociation

from nautobot_design_builder.errors import DesignImplementationError


class ModelField(ABC):
    """This represents any type of field (attribute or relationship) on a Nautobot model."""

    @abstractmethod
    def set_value(self, value):
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

    field: DjangoField
    model: Type[object]

    def __init__(self, model_instance, field: DjangoField):
        """Create a base model field.

        Args:
            model_instance (ModelInstance): Model instance which this field belongs to.
            field (DjangoField): Database field to be managed.
        """
        self.instance = model_instance
        self.field = field
        self.model = field.related_model

    @property
    def deferrable(self):  # noqa:D102
        return False


class SimpleField(BaseModelField):
    """A field that accepts a scalar value."""

    def set_value(self, value):  # noqa:D102
        setattr(self.instance.instance, self.field.name, value)


class RelationshipField(BaseModelField):
    """Field that represents a relationship to another model."""

    @property
    def deferrable(self):  # noqa:D102
        return True


class OneToOneField(RelationshipField):
    """One to one relationship field."""

    def set_value(self, value):  # noqa:D102
        setattr(self.instance.instance, self.field.name, value)
        self.instance.instance.save()


class OneToManyField(RelationshipField):
    """One to many relationship field."""

    def set_value(self, value):  # noqa:D102
        getattr(self.instance.instance, self.field.name).add(value, bulk=False)
        self.instance.instance.validated_save()
        value.validated_save()


class ManyToManyField(RelationshipField):
    """Many to many relationship field."""

    def __init__(self, model_instance, field: DjangoField):  # noqa:D102
        super().__init__(model_instance, field)
        if hasattr(field.remote_field, "through"):
            through = field.remote_field.through
            if not through._meta.auto_created:
                self.model = through

    def set_value(self, value):  # noqa:D102
        getattr(self.instance.instance, self.field.name).add(value)


class GenericRelationField(RelationshipField):
    """Generic relationship field."""

    def set_value(self, value):  # noqa:D102
        getattr(self.instance.instance, self.field.name).add(value)


class GenericForeignKeyField(RelationshipField):
    """Generic foreign key field."""

    @property
    def deferrable(self):  # noqa:D102
        return False

    def set_value(self, value):  # noqa:D102
        fk_field = self.field.fk_field
        ct_field = self.field.ct_field
        if hasattr(value, "instance"):
            value = value.instance
        setattr(self.instance.instance, fk_field, value.pk)
        setattr(self.instance.instance, ct_field, ContentType.objects.get_for_model(value))


class TagField(ManyToManyField):
    """Taggit field."""

    def __init__(self, model_instance, field: DjangoField):  # noqa:D102
        super().__init__(model_instance, field)
        self.model = field.remote_field.model


class ManyToOneField(RelationshipField):
    """Many to one relationship field."""

    @property
    def deferrable(self):  # noqa:D102
        return False

    def set_value(self, value):  # noqa:D102
        if isinstance(value, Mapping):
            try:
                includes_action = False
                for key in value.keys():
                    if key.startswith("!"):
                        includes_action = True
                if not includes_action:
                    value = {f"!get:{key}": value for key, value in value.items()}
                value = self.instance.create_child(self.model, value)
                if value.created:
                    value.save()
                value = value.instance.pk
            except MultipleObjectsReturned:
                # pylint: disable=raise-missing-from
                raise DesignImplementationError(
                    f"Expected exactly 1 object for {self.model.__name__}({value}) but got more than one"
                )
            except ObjectDoesNotExist:
                query = ",".join([f'{k}="{v}"' for k, v in value.items()])
                # pylint: disable=raise-missing-from
                raise DesignImplementationError(f"Could not find {self.model.__name__}: {query}")
        elif hasattr(value, "instance"):
            value = value.instance.pk
        elif isinstance(value, Model):
            value = value.pk
        elif value is not None:
            raise DesignImplementationError(
                f"Expecting input field '{self.field.name}' to be a mapping or reference, got {type(value)}: {value}"
            )
        setattr(self.instance.instance, self.field.attname, value)


class CustomRelationshipField(ModelField):  # pylint: disable=too-few-public-methods
    """This class models a Nautobot custom relationship."""

    def __init__(self, model_instance: Model, relationship: Relationship):
        """Create a new custom relationship field.

        Args:
            relationship (Relationship): The Nautobot custom relationship backing this field.
            model_class (Model): Model class for the remote end of this relationship.
            model_instance (ModelInstance): Object being updated to include this field.
        """
        self.relationship = relationship
        self.instance = model_instance
        self.one_to_one = relationship.type == RelationshipTypeChoices.TYPE_ONE_TO_ONE
        self.many_to_one = relationship.type == RelationshipTypeChoices.TYPE_ONE_TO_MANY
        self.one_to_many = self.many_to_one
        self.many_to_many = relationship.type == RelationshipTypeChoices.TYPE_MANY_TO_MANY
        if self.relationship.source_type == ContentType.objects.get_for_model(model_instance.model_class):
            self.model = relationship.destination_type.model_class()
        else:
            self.model = relationship.source_type.model_class()

    @property
    def deferrable(self):  # noqa:D102
        return True

    def set_value(self, value: Model):  # noqa:D102
        """Add an association between the created object and the given value.

        Args:
            value (Model): The related object to add.
        """
        source = self.instance.instance
        destination = value
        if self.relationship.source_type == ContentType.objects.get_for_model(value):
            source = value
            destination = self.instance.instance

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
    elif isinstance(arg2, GenericRelation):
        field = GenericRelationField(arg1, arg2)
    elif isinstance(arg2, GenericForeignKey):
        field = GenericForeignKeyField(arg1, arg2)
    elif isinstance(arg2, TaggableManager):
        field = TagField(arg1, arg2)
    elif arg2.one_to_one:
        field = OneToOneField(arg1, arg2)
    elif arg2.one_to_many:
        field = OneToManyField(arg1, arg2)
    elif arg2.many_to_many:
        field = ManyToManyField(arg1, arg2)
    elif arg2.many_to_one:
        field = ManyToOneField(arg1, arg2)
    else:
        raise DesignImplementationError(f"Cannot manufacture field for {type(arg2)}, {arg2} {arg2.is_relation}")
    return field
