"""Nested serializers for design builder."""

from nautobot.core.api import BaseModelSerializer
from rest_framework.relations import HyperlinkedIdentityField

from nautobot_design_builder.models import Design, Deployment, ChangeSet


class NestedDesignSerializer(BaseModelSerializer):
    """Nested serializer for the design model."""

    url = HyperlinkedIdentityField(view_name="plugins-api:nautobot_design_builder-api:design-detail")

    class Meta:
        """Nested serializer options for the design model."""

        model = Design
        fields = ["id", "url", "name"]


class NestedDeploymentSerializer(BaseModelSerializer):
    """Nested serializer for the design instance model."""

    url = HyperlinkedIdentityField(view_name="plugins-api:nautobot_design_builder-api:deployment-detail")

    class Meta:
        """Nested serializer options for the design instance model."""

        model = Deployment
        fields = ["id", "url", "name"]


class NestedChangeSetSerializer(BaseModelSerializer):
    """Nested serializer for the ChangeSet model."""

    url = HyperlinkedIdentityField(view_name="plugins-api:nautobot_design_builder-api:changeset-detail")

    class Meta:
        """Nested serializer options for the ChangeSet model."""

        model = ChangeSet
        fields = ["id", "url"]
