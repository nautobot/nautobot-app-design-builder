"""Serializers for design builder."""

from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema_field
from nautobot.apps.api import (
    NautobotModelSerializer,
    TaggedModelSerializerMixin,
)
from nautobot.apps.exceptions import SerializerNotFound
from nautobot.core.api import ContentTypeField
from nautobot.core.api.utils import (
    get_nested_serializer_depth,
    return_nested_serializer_data_based_on_depth,
)
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ReadOnlyField

from nautobot_design_builder.models import ChangeRecord, ChangeSet, Deployment, Design


class DesignSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for the design model."""

    name = ReadOnlyField()

    class Meta:
        """Serializer options for the design model."""

        model = Design
        fields = "__all__"


class DeploymentSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for the Deployment model."""

    created_by = SerializerMethodField()
    last_updated_by = SerializerMethodField()

    class Meta:
        """Serializer options for the design model."""

        model = Deployment
        fields = "__all__"

    def get_created_by(self, instance):
        """Get the username of the user who created the object."""
        return instance.created_by

    def get_last_updated_by(self, instance):
        """Get the username of the user who update the object last time."""
        return instance.last_updated_by


class ChangeSetSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for the change set model."""

    class Meta:
        """Serializer options for the change set model."""

        model = ChangeSet
        fields = "__all__"


class ChangeRecordSerializer(NautobotModelSerializer):
    """Serializer for the change record model."""

    _design_object_type = ContentTypeField(queryset=ContentType.objects.all(), label="design_object_type")
    design_object = SerializerMethodField(read_only=True)

    class Meta:
        """Serializer options for the change record  model."""

        model = ChangeRecord
        fields = "__all__"

    @extend_schema_field({"type": "object", "nullable": True})
    def get_design_object(self, obj):
        """Get design object serialized."""
        if obj.design_object:
            try:
                depth = get_nested_serializer_depth(self)
                return return_nested_serializer_data_based_on_depth(
                    self, depth, obj, obj.design_object, "design_object"
                )
            except SerializerNotFound:
                return None
        return None
