"""Filters for the design builder app."""
from nautobot.apps.filters import NautobotFilterSet, NaturalKeyOrPKMultipleChoiceFilter
from nautobot.extras.models import Job, JobResult
from nautobot.utilities.filters import SearchFilter

from nautobot_design_builder.models import Design, DesignInstance, Journal, JournalEntry


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


class DesignInstanceFilterSet(NautobotFilterSet):
    """Filter set for the design instance model."""
    q = SearchFilter(filter_predicates={})

    design = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Design.objects.all(),
        label="Design (ID or slug)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = DesignInstance
        fields = ["id", "design", "name", "owner", "first_implemented", "last_implemented"]


class JournalFilterSet(NautobotFilterSet):
    """Filter set for the journal model."""
    q = SearchFilter(filter_predicates={})

    design_instance = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DesignInstance.objects.all(),
        label="Design Instance (ID)",
    )

    job_result = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=JobResult.objects.all(),
        label="Job Result (ID)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = Journal
        fields = ["id", "design_instance", "job_result"]


class JournalEntryFilterSet(NautobotFilterSet):
    """Filter set for the journal entrymodel."""
    q = SearchFilter(filter_predicates={})

    journal = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Journal.objects.all(),
        label="Journal (ID)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = JournalEntry
        # TODO: Support design_object somehow?
        fields = ["id", "journal", "changes", "full_control"]
