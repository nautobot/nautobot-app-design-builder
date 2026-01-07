"""UI Views for design builder."""

from nautobot.extras.api.views import NautobotModelViewSet

from nautobot_design_builder.api.serializers import (
    ChangeRecordSerializer,
    ChangeSetSerializer,
    DeploymentSerializer,
    DesignSerializer,
)
from nautobot_design_builder.filters import (
    ChangeRecordFilterSet,
    ChangeSetFilterSet,
    DeploymentFilterSet,
    DesignFilterSet,
)
from nautobot_design_builder.models import ChangeRecord, ChangeSet, Deployment, Design


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


class ChangeSetAPIViewSet(NautobotModelViewSet):
    """API views for the change set model."""

    queryset = ChangeSet.objects.all()
    serializer_class = ChangeSetSerializer
    filterset_class = ChangeSetFilterSet


class ChangeRecordAPIViewSet(NautobotModelViewSet):
    """API views for the change record model."""

    queryset = ChangeRecord.objects.all()
    serializer_class = ChangeRecordSerializer
    filterset_class = ChangeRecordFilterSet
