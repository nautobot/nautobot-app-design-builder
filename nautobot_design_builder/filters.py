"""Filters for the design builder app."""

from nautobot.apps.filters import (
    NaturalKeyOrPKMultipleChoiceFilter,
    NautobotFilterSet,
    SearchFilter,
    StatusModelFilterSetMixin,
)
from nautobot.extras.models import Job, JobResult

from nautobot_design_builder.models import ChangeRecord, ChangeSet, Deployment, Design


class DesignFilterSet(NautobotFilterSet):
    """Filter set for the design model."""

    q = SearchFilter(
        filter_predicates={
            "job__name": "icontains",
        }
    )

    job = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Job.objects.all(),
        label="Job (ID or slug)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = Design
        fields = "__all__"


class DeploymentFilterSet(NautobotFilterSet, StatusModelFilterSetMixin):
    """Filter set for the Deployment model."""

    q = SearchFilter(
        filter_predicates={
            "design__job__name": "icontains",
            "name": "icontains",
            "version": "icontains",
        }
    )

    design = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Design.objects.all(),
        to_field_name="job_name",
        label="Design (ID or slug)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = Deployment
        fields = "__all__"


class ChangeSetFilterSet(NautobotFilterSet):
    """Filter set for the ChangeSet model."""

    q = SearchFilter(filter_predicates={})

    deployment = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Deployment.objects.all(),
        label="Design Deployment (ID)",
    )

    job_result = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=JobResult.objects.all(),
        label="Job Result (ID)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = ChangeSet
        fields = "__all__"


class ChangeRecordFilterSet(NautobotFilterSet):
    """Filter set for the ChangeRecord model."""

    q = SearchFilter(filter_predicates={})

    change_set = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ChangeSet.objects.all(),
        label="Change Set (ID)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = ChangeRecord
        fields = "__all__"
