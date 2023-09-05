"""UI Views for design builder."""
from nautobot.extras.api.views import NautobotModelViewSet

from nautobot_design_builder.api.serializers import (
    DesignSerializer,
    DesignInstanceSerializer,
    JournalSerializer,
    JournalEntrySerializer,
)
from nautobot_design_builder.filters import (
    DesignFilterSet,
    DesignInstanceFilterSet,
    JournalFilterSet,
    JournalEntryFilterSet,
)
from nautobot_design_builder.models import Design, DesignInstance, Journal, JournalEntry


class DesignAPIViewSet(NautobotModelViewSet):
    """API views for the design model."""

    queryset = Design.objects.all()
    serializer_class = DesignSerializer
    filterset_class = DesignFilterSet


class DesignInstanceAPIViewSet(NautobotModelViewSet):
    """API views for the design instance model."""

    queryset = DesignInstance.objects.all()
    serializer_class = DesignInstanceSerializer
    filterset_class = DesignInstanceFilterSet


class JournalAPIViewSet(NautobotModelViewSet):
    """API views for the journal model."""

    queryset = Journal.objects.all()
    serializer_class = JournalSerializer
    filterset_class = JournalFilterSet


class JournalEntryAPIViewSet(NautobotModelViewSet):
    """API views for the journal entry model."""

    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer
    filterset_class = JournalEntryFilterSet
