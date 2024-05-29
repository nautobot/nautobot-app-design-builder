"""UI Views for design builder."""

from nautobot.extras.api.views import NautobotModelViewSet

from nautobot_design_builder.api.serializers import (
    DesignSerializer,
    DeploymentSerializer,
    JournalSerializer,
    JournalEntrySerializer,
)
from nautobot_design_builder.filters import (
    DesignFilterSet,
    DeploymentFilterSet,
    JournalFilterSet,
    JournalEntryFilterSet,
)
from nautobot_design_builder.models import Design, Deployment, Journal, JournalEntry


class DesignAPIViewSet(NautobotModelViewSet):
    """API views for the design model."""

    queryset = Design.objects.all()
    serializer_class = DesignSerializer
    filterset_class = DesignFilterSet


class DeploymentAPIViewSet(NautobotModelViewSet):
    """API views for the design instance model."""

    queryset = Deployment.objects.all()
    serializer_class = DeploymentSerializer
    filterset_class = DeploymentFilterSet


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
