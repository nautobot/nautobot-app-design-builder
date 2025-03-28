"""API serializers for nautobot_design_builder."""

from nautobot.apps.api import NautobotModelSerializer, TaggedModelSerializerMixin

from nautobot_design_builder import models


class DesignSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):  # pylint: disable=too-many-ancestors
    """Design Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.Design
        fields = "__all__"

        # Option for disabling write for certain fields:
        # read_only_fields = []
