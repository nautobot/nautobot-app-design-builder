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
from logging import getLogger
from typing import TYPE_CHECKING, Any, Mapping, Type

from django.contrib.contenttypes import fields as ct_fields
from django.contrib.contenttypes.models import ContentType
from django.db import models as django_models
from nautobot.core.graphql.utils import str_to_var_name
from nautobot.extras.models import Relationship, RelationshipAssociation
from taggit.managers import TaggableManager

from nautobot_design_builder.changes import change_log
from nautobot_design_builder.debug import debug_set
from nautobot_design_builder.errors import DesignImplementationError, FieldNameError

if TYPE_CHECKING:
    from .design import ModelInstance

LOGGER = getLogger(__name__)


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
        if obj is None or obj.design_instance is None:
            return self
        return getattr(obj.design_instance, self.field_name)

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
            setattr(obj.design_instance, self.field_name, value)


class RelationshipFieldMixin:  # pylint:disable=too-few-public-methods
    """Field mixin for relationships to other models.

    `RelationshipField` instances represent fields that have some sort of relationship
    to other objects. These include `ForeignKey` and `ManyToMany`.
    Relationship fields also include the reverse side of fields or even custom relationships.
    """

    def _get_instance(
        self, obj: "ModelInstance", value: Any, relationship_manager: django_models.Manager = None, related_model=None
    ):
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

            related_model: The model class to use for creating new children. Defaults to the
              field's related model.

        Returns:
            ModelInstance: Either a newly created `ModelInstance` or the original value.
        """
        if related_model is None:
            related_model = self.related_model
        if isinstance(value, Mapping):
            value = obj.design_metadata.create_child(related_model, value, relationship_manager)
        return value


class ForeignKeyField(BaseModelField, RelationshipFieldMixin):  # pylint:disable=too-few-public-methods
    """`ForeignKey` relationship."""

    @debug_set
    def __set__(self, obj: "ModelInstance", value):  # noqa: D105
        deferred = getattr(value, "deferred", False) or (isinstance(value, Mapping) and value.get("deferred", False))

        def setter():
            model_instance = self._get_instance(obj, value)
            if model_instance.design_metadata.created:
                model_instance.save()

            with change_log(obj, self.field.attname):
                setattr(obj.design_instance, self.field_name, model_instance.design_instance)

            if deferred:
                obj.design_instance.save(update_fields=[self.field_name])

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
                    setattr(value.design_instance, self.field.field.name, obj.design_instance)
                value.save()

        obj.connect("POST_INSTANCE_SAVE", setter)


class ManyToManyField(BaseModelField, RelationshipFieldMixin):  # pylint:disable=too-few-public-methods
    """Many to many relationship field."""

    def __init__(self, field: django_models.Field):  # noqa:D102,D107
        super().__init__(field)
        self.auto_through = True
        self._init_through()

    def _init_through(self):
        self.through = self.field.remote_field.through
        if not self.through._meta.auto_created:
            self.auto_through = False
            if self.field.remote_field.through_fields:
                self.link_field = self.field.remote_field.through_fields[0]
            else:
                for field in self.through._meta.fields:
                    if field.related_model == self.field.model:
                        self.link_field = field.name

    def _get_related_model(self, value):
        """Get the appropriate related model for the value.

        if there is an explicit through class, then we have two choices:
        1) Assign explicitly using the through-class attributes
        2) Assign implicitly like a normal many-to-many

        We want to be able to handle both situations, because it may be that
        the through class has additional attributes. The way we determine if
        the design is requesting the through-class or the implicit related class
        is by examining the values to be assigned and matching their keys with
        the related model and through model.
        """
        if isinstance(value, Mapping):
            attributes = set()
            # Extract all of the top-level field names from the query in order
            # to match them against available fields in the through table. If
            # the set of attributes is a subset of the through class's attributes
            # then use the through class directly, otherwise use the related_model
            # class
            for attribute in value.keys():
                if attribute.startswith("!get") or attribute.startswith("!create"):
                    attribute_parts = attribute.split(":")
                    attribute = attribute_parts[1]

                if "__" in attribute:
                    attribute = attribute.split("__")[0]
                attributes.add(attribute)
            through_fields = set(field.name for field in self.through._meta.fields)
            if self.auto_through is False and attributes.issubset(through_fields):
                return self.through, attributes.intersection(through_fields)
        return self.related_model, set()

    @debug_set
    def __set__(self, obj: "ModelInstance", values):  # noqa:D105
        def setter():
            items = []
            for value in values:
                related_model, through_fields = self._get_related_model(value)
                relationship_manager = getattr(obj.design_instance, self.field_name).model.objects
                if through_fields:
                    value[f"!create_or_update:{self.link_field}_id"] = str(obj.design_instance.id)
                    relationship_manager = self.through.objects

                for field in through_fields:
                    value[f"!create_or_update:{field}"] = value.pop(field)
                value = self._get_instance(obj, value, relationship_manager, related_model)
                if related_model is not self.through:
                    items.append(value.design_instance)
                else:
                    setattr(value.design_instance, self.link_field, obj.design_instance)
                if value.design_metadata.created:
                    value.save()
            if items:
                with change_log(obj, self.field_name):
                    getattr(obj.design_instance, self.field_name).add(*items)

        obj.connect("POST_INSTANCE_SAVE", setter)


class ManyToManyRelField(ManyToManyField):  # pylint:disable=too-few-public-methods
    """Reverse many to many relationship field."""

    def _init_through(self):
        self.through = self.field.through
        if not self.through._meta.auto_created:
            self.auto_through = False
            if self.field.through_fields:
                self.link_field = self.field.through_fields[0]
            else:
                for field in self.through._meta.fields:
                    if field.related_model == self.field.model:
                        self.link_field = field.name


class GenericRelationField(BaseModelField, RelationshipFieldMixin):  # pylint:disable=too-few-public-methods
    """Generic relationship field."""

    @debug_set
    def __set__(self, obj: "ModelInstance", values):  # noqa:D105
        if not isinstance(values, list):
            values = [values]
        items = []
        for value in values:
            value = self._get_instance(obj, value)
            if value.design_metadata.created:
                value.save()
            items.append(value.design_instance)
        with change_log(obj, self.field_name):
            getattr(obj.design_instance, self.field_name).add(*items)


class GenericForeignKeyField(BaseModelField, RelationshipFieldMixin):  # pylint:disable=too-few-public-methods
    """Generic foreign key field."""

    @debug_set
    def __set__(self, obj: "ModelInstance", value):  # noqa:D105
        fk_field = self.field.fk_field
        ct_field = self.field.ct_field
        ct_id_field = obj.design_instance._meta.get_field(ct_field).attname
        with change_log(obj, fk_field), change_log(obj, ct_id_field):
            setattr(obj.design_instance, fk_field, value.design_instance.pk)
            setattr(obj.design_instance, ct_field, ContentType.objects.get_for_model(value.design_instance))


class TagField(BaseModelField, RelationshipFieldMixin):  # pylint:disable=too-few-public-methods
    """Taggit field."""

    def __init__(self, field: django_models.Field):  # noqa:D102,D107
        super().__init__(field)
        self.related_model = field.remote_field.model

    def __set__(self, obj: "ModelInstance", values):  # noqa:D105
        # I hate that this code is almost identical to the ManyToManyField
        # __set__ code, but I don't see an easy way to DRY it up at the
        # moment.
        def setter():
            items = []
            for value in values:
                value = self._get_instance(obj, value, getattr(obj.design_instance, self.field_name))
                if value.design_metadata.created:
                    value.save()
                items.append(value.design_instance)
            if items:
                with change_log(obj, self.field_name):
                    getattr(obj.design_instance, self.field_name).add(*items)

        obj.connect("POST_INSTANCE_SAVE", setter)


class GenericRelField(BaseModelField, RelationshipFieldMixin):  # pylint:disable=too-few-public-methods
    """Field used as part of content-types generic relation."""

    @debug_set
    def __set__(self, obj: "ModelInstance", value):  # noqa:D105
        with change_log(obj, self.field.attname):
            setattr(obj.design_instance, self.field.attname, self._get_instance(obj, value))


class CustomRelationshipField(ModelField, RelationshipFieldMixin):  # pylint: disable=too-few-public-methods
    """This class models a Nautobot custom relationship.

    When a design builder model class is created, custom relationships are
    retrieved for the underlying content-type. Each of these relationships is
    then added to the design builder proxy model as new properties. The property
    name is derived from the source or destination of the label, based on which
    side matches the underlying content-type. The relationship label will return
    the verbose_name_plural of the other side object if no label has been set.

    It should be noted that if a custom relationship's label matches a built-in
    field, then the proxy model will use the built-in field and the custom
    relationship will not be accessible. Additionally, a warning will be logged
    that a potential naming conflict exists.
    """

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
            field_name = str(self.relationship.get_label("source")).lower()
        else:
            self.related_model = relationship.source_type.model_class()
            field_name = str(self.relationship.get_label("destination")).lower()
        if hasattr(model_class.model_class, field_name):
            raise FieldNameError(model_class, relationship, field_name)
        self.__set_name__(model_class, str_to_var_name(field_name))
        self.key_name = self.relationship.key

    @debug_set
    def __set__(self, obj: "ModelInstance", values):  # noqa:D105
        """Add an association between the created object and the given value.

        Args:
            obj: (ModelInstance): The object receiving this attribute setter.

            values (Model): The related objects to add.
        """

        def setter():
            for value in values:
                value = self._get_instance(obj, value)
                if value.design_metadata.created:
                    value.save()

                source = obj.design_instance
                destination = value.design_instance
                if self.relationship.source_type == ContentType.objects.get_for_model(destination):
                    source, destination = destination, source

                source_type = ContentType.objects.get_for_model(source)
                destination_type = ContentType.objects.get_for_model(destination)
                relationship_association = obj.design_metadata.create_child(
                    RelationshipAssociation,
                    attributes={
                        "relationship_id": self.relationship.id,
                        "source_id": source.id,
                        "source_type_id": source_type.id,
                        "destination_id": destination.id,
                        "destination_type_id": destination_type.id,
                    },
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
    elif isinstance(arg2, django_models.ManyToManyField):
        field = ManyToManyField(arg2)
    elif isinstance(arg2, django_models.ManyToManyRel):
        field = ManyToManyRelField(arg2)
    else:
        raise DesignImplementationError(f"Cannot manufacture field for {type(arg2)}, {arg2} {arg2.is_relation}")
    return field
