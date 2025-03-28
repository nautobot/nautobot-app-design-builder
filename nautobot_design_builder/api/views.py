"""API views for nautobot_design_builder."""

from nautobot.apps.api import NautobotModelViewSet

from nautobot_design_builder import filters, models
from nautobot_design_builder.api import serializers


class DesignViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """Design viewset."""

    queryset = models.Design.objects.all()
    serializer_class = serializers.DesignSerializer
    filterset_class = filters.DesignFilterSet

    # Option for modifying the default HTTP methods:
    # http_method_names = ["get", "post", "put", "patch", "delete", "head", "options", "trace"]
