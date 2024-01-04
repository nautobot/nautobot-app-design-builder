"""Forms for the design builder app."""
from django.forms import NullBooleanField
from nautobot.extras.forms import NautobotFilterForm
from nautobot.extras.models import Job, JobResult
from nautobot.utilities.forms import TagFilterField, DynamicModelChoiceField, StaticSelect2, BOOLEAN_WITH_BLANK_CHOICES

from nautobot_design_builder.models import Design, DesignInstance, Journal, JournalEntry


class DesignFilterForm(NautobotFilterForm):
    """Filter form for the design model."""

    model = Design

    job = DynamicModelChoiceField(queryset=Job.objects.all())
    tag = TagFilterField(model)


class DesignInstanceFilterForm(NautobotFilterForm):
    """Filter form for the design instance model."""

    model = DesignInstance

    design = DynamicModelChoiceField(queryset=Design.objects.all())
    tag = TagFilterField(model)


class JournalFilterForm(NautobotFilterForm):
    """Filter form for the journal model."""

    model = Journal

    design_instance = DynamicModelChoiceField(queryset=DesignInstance.objects.all())
    job_result = DynamicModelChoiceField(queryset=JobResult.objects.all())
    tag = TagFilterField(model)


class JournalEntryFilterForm(NautobotFilterForm):
    """Filter form for the journal entry model."""

    model = JournalEntry

    journal = DynamicModelChoiceField(queryset=Journal.objects.all())
    full_control = NullBooleanField(
        required=False,
        label="Does the design have full control over the object?",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
