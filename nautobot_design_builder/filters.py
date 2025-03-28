"""Filtering for nautobot_design_builder."""

from nautobot.apps.filters import NameSearchFilterSet, NautobotFilterSet

from nautobot_design_builder import models


class DesignFilterSet(NautobotFilterSet, NameSearchFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for Design."""

    class Meta:
        """Meta attributes for filter."""

        model = models.Design

        # add any fields from the model that you would like to filter your searches by using those
        fields = ["id", "name", "description"]
