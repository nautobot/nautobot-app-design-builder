"""Serializers for design builder."""

from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema_field
from nautobot.apps.api import NautobotModelSerializer, TaggedModelSerializerMixin
from nautobot.core.api import ContentTypeField
from nautobot.core.api.utils import get_serializer_for_model
from rest_framework.fields import DictField, SerializerMethodField
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

    @extend_schema_field(DictField())
    def get_design_object(self, obj):
        """Get design object serialized."""
        if obj.design_object:
            serializer = get_serializer_for_model(obj.design_object)
            context = {"request": self.context["request"]}
            return serializer(obj.design_object, context=context).data
        return None
