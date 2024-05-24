"""Forms for the design builder app."""

from django.forms import NullBooleanField, CharField
from nautobot.extras.forms import NautobotFilterForm
from nautobot.extras.models import Job, JobResult
from nautobot.utilities.forms import TagFilterField, DynamicModelChoiceField, StaticSelect2, BOOLEAN_WITH_BLANK_CHOICES

from nautobot_design_builder.models import Design, Deployment, ChangeSet, ChangeRecord


class DesignFilterForm(NautobotFilterForm):
    """Filter form for the design model."""

    model = Design

    job = DynamicModelChoiceField(queryset=Job.objects.all(), required=False)
    tag = TagFilterField(model)
    version = CharField(max_length=20, required=False)


class DeploymentFilterForm(NautobotFilterForm):
    """Filter form for the design instance model."""

    model = Deployment

    design = DynamicModelChoiceField(queryset=Design.objects.all())
    tag = TagFilterField(model)
    version = CharField(max_length=20, required=False)


class ChangeSetFilterForm(NautobotFilterForm):
    """Filter form for the ChangeSet model."""

    model = ChangeSet

    deployment = DynamicModelChoiceField(queryset=Deployment.objects.all())
    job_result = DynamicModelChoiceField(queryset=JobResult.objects.all())
    tag = TagFilterField(model)


class ChangeRecordFilterForm(NautobotFilterForm):
    """Filter form for the ChangeRecord entry model."""

    model = ChangeRecord

    change_set = DynamicModelChoiceField(queryset=ChangeSet.objects.all())
    full_control = NullBooleanField(
        required=False,
        label="Does the design have full control over the object?",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
