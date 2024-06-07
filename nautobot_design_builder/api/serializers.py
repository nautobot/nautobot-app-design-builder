"""Serializers for design builder."""

from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema_field
from nautobot.apps.api import NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin
from nautobot.core.api import ContentTypeField
from nautobot.extras.api.nested_serializers import NestedJobResultSerializer
from nautobot.utilities.api import get_serializer_for_model
from rest_framework.fields import SerializerMethodField, DictField
from rest_framework.relations import HyperlinkedIdentityField

from nautobot_design_builder.models import Design, Deployment, ChangeSet, ChangeRecord

from nautobot_design_builder.api.nested_serializers import (
    NestedDesignSerializer,
    NestedDeploymentSerializer,
    NestedChangeSetSerializer,
)


class DesignSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for the design model."""

    url = HyperlinkedIdentityField(view_name="plugins-api:nautobot_design_builder-api:design-detail")

    class Meta:
        """Serializer options for the design model."""

        model = Design
        fields = [
            "id",
            "url",
            "name",
        ]


class DeploymentSerializer(NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin):
    """Serializer for the design instance model."""

    url = HyperlinkedIdentityField(view_name="plugins-api:nautobot_design_builder-api:design-detail")
    design = NestedDesignSerializer()
    created_by = SerializerMethodField()
    last_updated_by = SerializerMethodField()

    class Meta:
        """Serializer options for the design model."""

        model = Deployment
        fields = [
            "id",
            "url",
            "design",
            "name",
            "created_by",
            "first_implemented",
            "last_updated_by",
            "last_implemented",
            "status",
        ]

    def get_created_by(self, instance):
        """Get the username of the user who created the object."""
        return instance.created_by

    def get_last_updated_by(self, instance):
        """Get the username of the user who update the object last time."""
        return instance.last_updated_by


class ChangeSetSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for the ChangeSet model."""

    url = HyperlinkedIdentityField(view_name="plugins-api:nautobot_design_builder-api:changeset-detail")
    deployment = NestedDeploymentSerializer()
    job_result = NestedJobResultSerializer()

    class Meta:
        """Serializer options for the ChangeSet model."""

        model = ChangeSet
        fields = ["id", "url", "deployment", "job_result"]


class ChangeRecordSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for the ChangeRecord model."""

    url = HyperlinkedIdentityField(view_name="plugins-api:nautobot_design_builder-api:changerecord-detail")
    change_set = NestedChangeSetSerializer()
    _design_object_type = ContentTypeField(queryset=ContentType.objects.all(), label="design_object_type")
    design_object = SerializerMethodField(read_only=True)

    class Meta:
        """Serializer options for the ChangeRecord model."""

        model = ChangeRecord
        fields = ["id", "url", "change_set", "_design_object_type", "design_object", "changes", "full_control"]

    @extend_schema_field(DictField())
    def get_design_object(self, obj):
        """Get design object serialized."""
        if obj.design_object:
            serializer = get_serializer_for_model(obj.design_object, prefix="Nested")
            context = {"request": self.context["request"]}
            return serializer(obj.design_object, context=context).data
        return None
