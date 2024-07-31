"""This module includes the proxy model field descriptors.

The way design builder handles attribute assignment is with descriptors. This
allows assignment of values directly to the proxy model and the descriptors
handle any necessary deferrals.

For instance, `ForeignKey` relationships require that foreign key object be
present in the database before the receiving object (object with the
`ForeignKey` field) can be saved. When design builder encounters this situation
there are some cases (for example, setting IP addresses on interfaces) where
assignment must be deferred in order to guarantee the parent object is present
in the database prior to save.

Another example is the reverse side of foreign key relationships. Consider a `Device` which
has many `Interface` objects. The device foreign key is defined on the `Interface` object,
but we would typically model this in design builder as such:

```yaml
devices:
  # additional attributes such as device type, role, location, etc
  # are not illustrated here.
  - name: "My Device"
    interfaces:
      - name: "Ethernet1"
        # type, status, etc
      - name: "Ethernet2"
        # type, status, etc
```

In order to save these objects to the database, the device must be saved first, and
then each interface's device foreign key is set and saved.

Since design builder generally processes things in a depth first order, the natural sequence
is for the interfaces (in the above example) to be created first. Therefore, the
`ManyToOneRelField` will handle creating an instance of Interface but deferring database
save until after the device is saved.

See also: https://docs.python.org/3/howto/descriptor.html
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Mapping, Type, TYPE_CHECKING

from django.db import models as django_models
from django.db.models.manager import Manager
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import fields as ct_fields

from taggit.managers import TaggableManager

from nautobot.core.graphql.utils import str_to_var_name
from nautobot.extras.models import Relationship, RelationshipAssociation

from nautobot_design_builder.errors import DesignImplementationError
from nautobot_design_builder.debug import debug_set

if TYPE_CHECKING:
    from .design import ModelInstance


def _get_change_value(value):
    if isinstance(value, Manager):
        value = {item.pk for item in value.all()}
    return value


@contextmanager
def change_log(model_instance: "ModelInstance", attr_name: str):
    """Log changes for a field.

    This context manager will record the value of a field prior to a change
    as well as the value after the change. If the values are different then
    a change record is added to the underlying model instance.

    Args:
        model_instance (ModelInstance): The model instance that is being updated.
        attr_name (str): The attribute to be updated.
    """
    old_value = _get_change_value(getattr(model_instance.instance, attr_name))
    yield
    new_value = _get_change_value(getattr(model_instance.instance, attr_name))
    if old_value != new_value or model_instance.environment.import_mode:

        if isinstance(old_value, set):
            model_instance.metadata.changes[attr_name] = {
                "old_items": old_value,
                "new_items": new_value,
            }
        else:
            model_instance.metadata.changes[attr_name] = {
                "old_value": old_value,
                "new_value": new_value,
            }


class ModelField(ABC):
    """This represents any type of field (attribute or relationship) on a Nautobot model.

    The design builder fields are descriptors that are used to build the
    correct relationship hierarchy of django models based on the design input.
    The fields are used to sequence saves and value assignments in the correct
    order.
    """

    field_name: str

    def __set_name__(self, owner, name):  # noqa: D105
        self.field_name = name

    def __get__(self, obj, objtype=None) -> Any:
        """Retrieve the field value.

        In the event `obj` is None (as in getting the attribute from the class) then
        get the descriptor itself.

        Args:
            obj (ModelInstance): The model to retrieve the field value
            objtype (type, optional): The owning class of the descriptor. Defaults to None.

        Returns:
            Any: Either the descriptor instance or the field value.
        """
        if obj is None or obj.instance is None:
            return self
        return getattr(obj.instance, self.field_name)

    @abstractmethod
    def __set__(self, obj: "ModelInstance", value):
        """Method used to set the value of the field.

        Args:
            obj: (ModelInstance): The model to update.
            value (Any): Value that should be set on the model field.
        """


class BaseModelField(ModelField):  # pylint:disable=too-few-public-methods
    """`BaseModelField` is backed by django.db.models.fields.Field.

    `BaseModelField` is used as the base class for any design builder field
    which proxies to a Django model field. Not all design builder fields are
    for actual model database fields. For instance, custom relationships are
    something design builder handles with a field descriptor, but they
    are not backed by django `Field` descriptors.
    """

    field: django_models.Field
    related_model: Type[object]

    def __init__(self, field: django_models.Field):
        """Initialize a field proxy.

        Args:
            field (django_models.Field): The field that should be proxied on the django model.
        """
        self.field = field
        self.field_name = field.name
        self.related_model = field.related_model


class SimpleField(BaseModelField):  # pylint:disable=too-few-public-methods
    """A field that accepts a scalar value.

    `SimpleField` will immediately set scalar values on the underlying field. This
    includes assignment to fields such as `CharField` or `IntegerField`. When
    this descriptor is called, the assigned value is immediately passed to the
    underlying model object.
    """

    @debug_set
    def __set__(self, obj: "ModelInstance", value):  # noqa: D105
        with change_log(obj, self.field_name):
            setattr(obj.instance, self.field_name, value)


class RelationshipFieldMixin:  # pylint:disable=too-few-public-methods
    """Field mixin for relationships to other models.

    `RelationshipField` instances represent fields that have some sort of relationship
    to other objects. These include `ForeignKey` and `ManyToMany`.
    Relationship fields also include the reverse side of fields or even custom relationships.
    """

    def _get_instance(self, obj: "ModelInstance", value: Any, relationship_manager: "Manager" = None):
        """Helper function to create a new child model from a value.

        If the passed-in value is a dictionary, this method assumes that the dictionary
        represents a new design builder object which will belong to a parent. In this
        case a new child is created from the parent object.

        If the value is not a dictionary, it is simply returned.

        Args:
            obj (ModelInstance): The parent object that the value will be ultimately assigned.
            value (Any): The value being assigned to the parent object.
            relationship_manager (Manager, optional): This argument can be used to restrict the
            child object lookups to a subset. For instance, the `interfaces` manager on a `Device`
            instance will restrict queries interfaces where their foreign key is set to the device.
            Defaults to None.

        Returns:
            ModelInstance: Either a newly created `ModelInstance` or the original value.
        """
        if isinstance(value, Mapping):
            value = obj.create_child(self.related_model, value, relationship_manager)
        return value


class ForeignKeyField(BaseModelField, RelationshipFieldMixin):  # pylint:disable=too-few-public-methods
    """`ForeignKey` relationship."""

    @debug_set
    def __set__(self, obj: "ModelInstance", value):  # noqa: D105
        deferred = getattr(value, "deferred", False) or (isinstance(value, Mapping) and value.get("deferred", False))

        def setter():
            model_instance = self._get_instance(obj, value)
            if model_instance.metadata.created:
                model_instance.save()
            else:
                model_instance.environment.journal.log(model_instance)

            with change_log(obj, self.field.attname):
                setattr(obj.instance, self.field_name, model_instance.instance)

            if deferred:
                obj.instance.save(update_fields=[self.field_name])

        if deferred:
            obj.connect("POST_INSTANCE_SAVE", setter)
        else:
            setter()


class ManyToOneRelField(BaseModelField, RelationshipFieldMixin):  # pylint:disable=too-few-public-methods
    """The reverse side of a `ForeignKey` relationship."""

    @debug_set
    def __set__(self, obj: "ModelInstance", values):  # noqa:D105
        if not isinstance(values, list):
            raise DesignImplementationError("Many-to-one fields must be a list", obj)

        def setter():
            for value in values:
                value = self._get_instance(obj, value, getattr(obj, self.field_name))
                with change_log(value, self.field.field.attname):
                    setattr(value.instance, self.field.field.name, obj.instance)
                value.save()

        obj.connect("POST_INSTANCE_SAVE", setter)


class ManyToManyField(BaseModelField, RelationshipFieldMixin):  # pylint:disable=too-few-public-methods
    """Many to many relationship field."""

    def __init__(self, field: django_models.Field):  # noqa:D102
        super().__init__(field)
        if hasattr(field.remote_field, "through"):
            through = field.remote_field.through
            if not through._meta.auto_created:
                self.related_model = through

    @debug_set
    def __set__(self, obj: "ModelInstance", values):  # noqa:D105
        def setter():
            items = []
            for value in values:
                value = self._get_instance(obj, value, getattr(obj.instance, self.field_name))
                if value.metadata.created:
                    value.save()
                else:
                    value.environment.journal.log(value)
                items.append(value.instance)
            with change_log(obj, self.field_name):
                getattr(obj.instance, self.field_name).add(*items)

        obj.connect("POST_INSTANCE_SAVE", setter)


class GenericRelationField(BaseModelField, RelationshipFieldMixin):  # pylint:disable=too-few-public-methods
    """Generic relationship field."""

    @debug_set
    def __set__(self, obj: "ModelInstance", values):  # noqa:D105
        if not isinstance(values, list):
            values = [values]
        items = []
        for value in values:
            value = self._get_instance(obj, value)
            if value.metadata.created:
                value.save()
            else:
                value.environment.journal.log(value)
            items.append(value.instance)
        with change_log(obj, self.field_name):
            getattr(obj.instance, self.field_name).add(*items)


class GenericForeignKeyField(BaseModelField, RelationshipFieldMixin):  # pylint:disable=too-few-public-methods
    """Generic foreign key field."""

    @debug_set
    def __set__(self, obj: "ModelInstance", value):  # noqa:D105
        fk_field = self.field.fk_field
        ct_field = self.field.ct_field
        ct_id_field = obj.instance._meta.get_field(ct_field).attname
        with change_log(obj, fk_field), change_log(obj, ct_id_field):
            setattr(obj.instance, fk_field, value.instance.pk)
            setattr(obj.instance, ct_field, ContentType.objects.get_for_model(value.instance))


class TagField(ManyToManyField):  # pylint:disable=too-few-public-methods
    """Taggit field."""

    def __init__(self, field: django_models.Field):  # noqa:D102
        super().__init__(field)
        self.related_model = field.remote_field.model


class GenericRelField(BaseModelField, RelationshipFieldMixin):  # pylint:disable=too-few-public-methods
    """Field used as part of content-types generic relation."""

    @debug_set
    def __set__(self, obj: "ModelInstance", value):  # noqa:D105
        with change_log(obj, self.field.attname):
            setattr(obj.instance, self.field.attname, self._get_instance(obj, value))


class CustomRelationshipField(ModelField, RelationshipFieldMixin):  # pylint: disable=too-few-public-methods
    """This class models a Nautobot custom relationship."""

    def __init__(self, model_class, relationship: Relationship):
        """Create a new custom relationship field.

        Args:
            model_class (Model): Model class for this relationship.
            relationship (Relationship): The Nautobot custom relationship backing this field.
        """
        self.relationship = relationship
        field_name = ""
        if self.relationship.source_type == ContentType.objects.get_for_model(model_class.model_class):
            self.related_model = relationship.destination_type.model_class()
            field_name = str(self.relationship.get_label("source"))
        else:
            self.related_model = relationship.source_type.model_class()
            field_name = str(self.relationship.get_label("destination"))
        self.__set_name__(model_class, str_to_var_name(field_name))
        self.key_name = self.relationship.slug

    @debug_set
    def __set__(self, obj: "ModelInstance", values):  # noqa:D105
        """Add an association between the created object and the given value.

        Args:
            values (Model): The related objects to add.
        """

        def setter():
            for value in values:
                value = self._get_instance(obj, value)
                if value.metadata.created:
                    value.save()
                else:
                    value.environment.journal.log(value)

                source = obj.instance
                destination = value.instance
                if self.relationship.source_type == ContentType.objects.get_for_model(destination):
                    source, destination = destination, source

                source_type = ContentType.objects.get_for_model(source)
                destination_type = ContentType.objects.get_for_model(destination)
                relationship_association = obj.environment.model_class_index[RelationshipAssociation](
                    environment=obj.environment,
                    attributes={
                        "relationship_id": self.relationship.id,
                        "source_id": source.id,
                        "source_type_id": source_type.id,
                        "destination_id": destination.id,
                        "destination_type_id": destination_type.id,
                    },
                    parent=obj,
                )
                relationship_association.save()

        obj.connect("POST_INSTANCE_SAVE", setter)


def field_factory(arg1, arg2) -> ModelField:
    """Factory function to create a ModelField."""
    if isinstance(arg2, Relationship):
        return CustomRelationshipField(arg1, arg2)

    field = None
    if not arg2.is_relation:
        field = SimpleField(arg2)
    elif isinstance(arg2, ct_fields.GenericRelation):
        field = GenericRelationField(arg2)
    elif isinstance(arg2, ct_fields.GenericRel):
        field = GenericRelField(arg2)
    elif isinstance(arg2, ct_fields.GenericForeignKey):
        field = GenericForeignKeyField(arg2)
    elif isinstance(arg2, TaggableManager):
        field = TagField(arg2)
    elif isinstance(arg2, django_models.ForeignKey):
        field = ForeignKeyField(arg2)
    elif isinstance(arg2, django_models.ManyToOneRel):
        field = ManyToOneRelField(arg2)
    elif isinstance(arg2, (django_models.ManyToManyField, django_models.ManyToManyRel)):
        field = ManyToManyField(arg2)
    else:
        raise DesignImplementationError(f"Cannot manufacture field for {type(arg2)}, {arg2} {arg2.is_relation}")
    return field
