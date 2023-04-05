from abc import ABC, abstractmethod, abstractproperty
from typing import Mapping, Type

from django.db.models.base import Model
from django.db.models.fields import Field as DjangoField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from taggit.managers import TaggableManager

from nautobot.core.models import BaseModel
from nautobot.extras.choices import RelationshipTypeChoices
from nautobot.extras.models import Relationship, RelationshipAssociation

from design_builder.errors import DesignImplementationError


class ModelField(ABC):
    @abstractmethod
    def set_value(self, value):
        pass

    @abstractproperty
    def deferrable(self):
        pass


class SimpleField(ModelField):
    def __init__(self, model_instance, field: DjangoField):
        self.instance = model_instance
        self.field = field

    def set_value(self, value):
        setattr(self.instance.instance, self.field.name, value)

    @property
    def deferrable(self):
        return False


class RelationshipField(SimpleField):
    field: DjangoField
    model: Type[object]

    def __init__(self, model_instance, field: DjangoField):
        self.instance = model_instance
        self.field = field

        self.model = field.related_model

    @property
    def deferrable(self):
        return True


class OneToOneField(RelationshipField):
    def set_value(self, value):
        setattr(self.instance.instance, self.field.name, value)


class OneToManyField(RelationshipField):
    def set_value(self, value):
        getattr(self.instance.instance, self.field.name).add(value, bulk=False)
        self.instance.instance.validated_save()
        value.validated_save()


class ManyToManyField(RelationshipField):
    def __init__(self, model_instance, field: DjangoField):
        super().__init__(model_instance, field)
        if hasattr(field.remote_field, "through"):
            through = field.remote_field.through
            if not through._meta.auto_created:
                self.model = through

    def set_value(self, value):
        getattr(self.instance.instance, self.field.name).add(value)


class GenericRelationField(RelationshipField):
    def set_value(self, value):
        getattr(self.instance.instance, self.field.name).add(value)


class TagField(ManyToManyField):
    def __init__(self, model_instance, field: DjangoField):
        super().__init__(model_instance, field)
        self.model = field.remote_field.model


class ManyToOneField(RelationshipField):
    @property
    def deferrable(self):
        return False

    def set_value(self, value):
        if isinstance(value, Mapping):
            try:
                value = self.model.objects.get(**value)  # pylint: disable=not-a-mapping
                setattr(self.instance.instance, self.field.name, value)
            except MultipleObjectsReturned:
                raise DesignImplementationError(
                    "Expected exactly 1 object for {self.model.__name__}({lookup}) but got more than one"
                )
            except ObjectDoesNotExist:
                query = ",".join([f'{k}="{v}"' for k, v in value.items()])
                raise DesignImplementationError(f"Could not find {self.model.__name__}: {query}")
        elif hasattr(value, "instance"):
            setattr(self.instance.instance, self.field.name, value.instance)
        elif isinstance(value, Model):
            setattr(self.instance.instance, self.field.name, value)
        else:
            raise DesignImplementationError(
                f"Expecting input field '{value} to be a mapping or reference, got {type(value)}: {value}"
            )


class CustomRelationshipField(ModelField):  # pylint: disable=too-few-public-methods
    """This class models a Nautobot custom relationship."""

    def __init__(self, model_instance, relationship: Relationship):
        """Create a new custom relationship field.

        Args:
            relationship (Relationship): The Nautobot custom relationship backing this field.
            model_class (BaseModel): Model class for the remote end of this relationship.
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
    def deferrable(self):
        return True

    def set_value(self, value: BaseModel):
        """Add an association between the created object and the given value.

        Args:
            value (BaseModel): The related object to add.
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


def Field(arg1, arg2) -> ModelField:
    if isinstance(arg2, Relationship):
        return CustomRelationshipField(arg1, arg2)

    if not arg2.is_relation:
        return SimpleField(arg1, arg2)
    if isinstance(arg2, GenericRelation):
        return GenericRelationField(arg1, arg2)
    if isinstance(arg2, TaggableManager):
        return TagField(arg1, arg2)
    if arg2.one_to_one:
        return OneToOneField(arg1, arg2)
    if arg2.one_to_many:
        return OneToManyField(arg1, arg2)
    if arg2.many_to_many:
        return ManyToManyField(arg1, arg2)
    if arg2.many_to_one:
        return ManyToOneField(arg1, arg2)
    raise DesignImplementationError(f"Cannot manufacture field for {type(arg2)}, {arg2} {arg2.is_relation}")
