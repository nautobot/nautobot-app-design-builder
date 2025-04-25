"""Filters for the design builder app."""

from django_filters import CharFilter
from nautobot.apps.filters import (
    NaturalKeyOrPKMultipleChoiceFilter,
    NautobotFilterSet,
    SearchFilter,
    StatusModelFilterSetMixin,
)
from nautobot.extras.models import Job, JobResult

from nautobot_design_builder.models import ChangeRecord, ChangeSet, Deployment, Design


class DesignFilterSet(NameSearchFilterSet, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for Design."""

    class Meta:
        """Meta attributes for filter."""

        model = Design
        fields = ["id", "name", "job"]

        # add any fields from the model that you would like to filter your searches by using those
        fields = "__all__"
