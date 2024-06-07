"""Filters for the design builder app."""

from nautobot.apps.filters import NautobotFilterSet, NaturalKeyOrPKMultipleChoiceFilter, StatusModelFilterSetMixin
from nautobot.extras.models import Job, JobResult
from nautobot.utilities.filters import SearchFilter

from nautobot_design_builder.models import Design, Deployment, ChangeSet, ChangeRecord


class DesignFilterSet(NautobotFilterSet):
    """Filter set for the design model."""

    q = SearchFilter(filter_predicates={})

    job = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Job.objects.all(),
        label="Job (ID or slug)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = Design
        fields = ["id", "job"]


class DeploymentFilterSet(NautobotFilterSet, StatusModelFilterSetMixin):
    """Filter set for the design instance model."""

    q = SearchFilter(filter_predicates={})

    design = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Design.objects.all(),
        label="Design (ID or slug)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = Deployment
        fields = [
            "id",
            "design",
            "name",
            "first_implemented",
            "last_implemented",
            "status",
            "version",
        ]


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
        fields = ["id", "deployment", "job_result"]


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
        # TODO: Support design_object somehow?
        fields = ["id", "change_set", "changes", "full_control"]
