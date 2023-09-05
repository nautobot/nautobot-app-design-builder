"""Serializers for design builder."""
from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema_field
from nautobot.apps.api import NautobotModelSerializer, TaggedModelSerializerMixin
from nautobot.core.api import ContentTypeField
from nautobot.extras.api.nested_serializers import NestedJobResultSerializer
from nautobot.utilities.api import get_serializer_for_model
from rest_framework.fields import SerializerMethodField, DictField
from rest_framework.relations import HyperlinkedIdentityField

from nautobot_design_builder.models import Design, DesignInstance, Journal, JournalEntry

from nautobot_design_builder.api.nested_serializers import (
    NestedDesignSerializer,
    NestedDesignInstanceSerializer,
    NestedJournalSerializer,
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


class DesignInstanceSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for the design instance model."""

    url = HyperlinkedIdentityField(view_name="plugins-api:nautobot_design_builder-api:design-detail")
    design = NestedDesignSerializer()

    class Meta:
        """Serializer options for the design model."""

        model = DesignInstance
        fields = [
            "id",
            "url",
            "design",
            "name",
            "owner",
            "first_implemented",
            "last_implemented",
        ]


class JournalSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for the journal model."""

    url = HyperlinkedIdentityField(view_name="plugins-api:nautobot_design_builder-api:journal-detail")
    design_instance = NestedDesignInstanceSerializer()
    job_result = NestedJobResultSerializer()

    class Meta:
        """Serializer options for the journal model."""

        model = Journal
        fields = ["id", "url", "design_instance", "job_result"]


class JournalEntrySerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for the journal entry model."""

    url = HyperlinkedIdentityField(view_name="plugins-api:nautobot_design_builder-api:journalentry-detail")
    journal = NestedJournalSerializer()
    _design_object_type = ContentTypeField(queryset=ContentType.objects.all(), label="design_object_type")
    design_object = SerializerMethodField(read_only=True)

    class Meta:
        """Serializer options for the journal entry model."""

        model = JournalEntry
        fields = ["id", "url", "journal", "_design_object_type", "design_object", "changes", "full_control"]

    @extend_schema_field(DictField())
    def get_design_object(self, obj):
        serializer = get_serializer_for_model(obj.design_object, prefix="Nested")
        context = {"request": self.context["request"]}
        return serializer(obj.design_object, context=context).data
