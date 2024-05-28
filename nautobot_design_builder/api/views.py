"""UI Views for design builder."""

from nautobot.extras.api.views import NautobotModelViewSet, StatusViewSetMixin

from nautobot_design_builder.api.serializers import (
    DesignSerializer,
    DeploymentSerializer,
    ChangeSetSerializer,
    ChangeRecordSerializer,
)
from nautobot_design_builder.filters import (
    DesignFilterSet,
    DeploymentFilterSet,
    ChangeSetFilterSet,
    ChangeRecordFilterSet,
)
from nautobot_design_builder.models import Design, Deployment, ChangeSet, ChangeRecord


class DesignAPIViewSet(NautobotModelViewSet):
    """API views for the design model."""

    queryset = Design.objects.all()
    serializer_class = DesignSerializer
    filterset_class = DesignFilterSet


class DeploymentAPIViewSet(NautobotModelViewSet, StatusViewSetMixin):
    """API views for the design instance model."""

    queryset = Deployment.objects.all()
    serializer_class = DeploymentSerializer
    filterset_class = DeploymentFilterSet


class ChangeSetAPIViewSet(NautobotModelViewSet):
    """API views for the ChangeSet model."""

    queryset = ChangeSet.objects.all()
    serializer_class = ChangeSetSerializer
    filterset_class = ChangeSetFilterSet


class ChangeRecordAPIViewSet(NautobotModelViewSet):
    """API views for the ChangeRecord entry model."""

    queryset = ChangeRecord.objects.all()
    serializer_class = ChangeRecordSerializer
    filterset_class = ChangeRecordFilterSet
