"""Tables for design builder."""

import django_tables2 as tables
from django.conf import settings
from django_tables2.utils import Accessor
from nautobot.apps.tables import BaseTable, BooleanColumn, ButtonsColumn, StatusTableMixin

from nautobot_design_builder import choices
from nautobot_design_builder.models import ChangeRecord, ChangeSet, Deployment, Design

DESIGN_TABLE = """

<li>
    <a role="button" data-href="{% url 'plugins:nautobot_design_builder:design_docs' pk=record.pk %}" class="dropdown-item" data-bs-toggle="modal" data-bs-target="#db-docs-modal">
        <span class="mdi mdi-file-document-outline"></span>
        Design Documentation
    </a>
</li>
<li>
    <a href="{% url 'extras:job_run_by_class_path' class_path=record.job.class_path %}" class="dropdown-item text-primary">
        <span class="mdi mdi-play"></span>
        Deploy Design
    </a>
</li>
<li>
    <a href="{% url 'extras:job_edit' pk=record.job.pk %}" class="dropdown-item text-warning">
        <span class="mdi mdi-pencil"></span>
        Edit Design Job
    </a>
</li>
"""


class DesignTable(BaseTable):
    """Table for list view."""

    name = tables.Column(linkify=True)
    design_mode = tables.Column(verbose_name="Mode")
    deployment_count = tables.Column(verbose_name="Deployments")
    actions = ButtonsColumn(Design, buttons=("changelog", "delete"), prepend_template=DESIGN_TABLE)
    job_last_synced = tables.Column(accessor="job.last_updated", verbose_name="Last Synced Time")

    def render_design_mode(self, value):
        """Lookup the human readable design mode from the assigned mode value."""
        return choices.DesignModeChoices.as_dict()[value]

    def render_deployment_count(self, value, record):
        """Calculate the number of deployments for a design.

        If the design is a deployment then return the count of deployments for the design. If
        the mode is `classic` then return a dash to indicate deployments aren't tracked in that
        mode.
        """
        if record.design_mode != choices.DesignModeChoices.CLASSIC:
            return value
        return "-"

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        """Meta attributes."""

        model = Design
        fields = ("name", "design_mode", "version", "job_last_synced", "description")


DEPLOYMENT_TABLE = """
{% load utils %}
<a href="{% url "extras:job_run_by_class_path" class_path="nautobot_design_builder.jobs.DeploymentDecommissioning" %}?deployments={{record.pk}}" class="btn btn-sm btn-primary" title="Decommission">
    <i class="mdi mdi-delete-sweep"></i>
</a>
<a href="{% url 'extras:job_run' pk=record.design.job.pk %}?kwargs_from_job_result={% with record|get_last_change_set as last_change_set %}{{ last_change_set.job_result.pk }}{% endwith %}"
    class="btn btn-sm btn-success" title="Re-run job with same arguments.">
    <i class="mdi mdi-repeat"></i>
</a>
"""


class DeploymentTable(StatusTableMixin, BaseTable):
    """Table for list view."""

    name = tables.Column(linkify=True)
    design = tables.Column(linkify=True)
    first_implemented = tables.Column(verbose_name="Deployment Time")
    last_implemented = tables.Column(verbose_name="Last Update Time")
    created_by = tables.Column(verbose_name="Deployed by")
    last_updated_by = tables.Column(verbose_name="Last Updated by")
    actions = ButtonsColumn(
        Deployment,
        buttons=(
            "delete",
            "changelog",
        ),
        prepend_template=DEPLOYMENT_TABLE,
    )

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        """Meta attributes."""

        model = Deployment
        fields = (
            "name",
            "design",
            "version",
            "created_by",
            "first_implemented",
            "last_updated_by",
            "last_implemented",
            "status",
        )


def linkify_design_object(value):
    """Attempt to linkify a design object.

    Some objects (through-classes for many-to-many as an example) don't
    really have a way to linkify, so those will return None.
    """
    try:
        return value.get_absolute_url()
    except AttributeError:
        return None


class DesignObjectsTable(BaseTable):  # pylint:disable=nb-sub-class-name
    """Table of objects that belong to a design instance."""

    design_object_type = tables.Column(verbose_name="Design Object Type", accessor="_design_object_type")
    design_object = tables.Column(linkify=linkify_design_object, verbose_name="Design Object")

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        """Meta attributes."""

        model = ChangeRecord
        fields = ("design_object_type", "design_object")


class ChangeSetTable(BaseTable):
    """Table for list view."""

    created = tables.DateTimeColumn(linkify=True, format=settings.SHORT_DATETIME_FORMAT)
    deployment = tables.Column(linkify=True, verbose_name="Deployment")
    job_result = tables.Column(
        accessor=Accessor("job_result.name"),
        linkify=lambda record: record.job_result.get_absolute_url(),
        verbose_name="Job Result",
    )
    record_count = tables.Column(accessor=Accessor("record_count"), verbose_name="Change Records")
    active = BooleanColumn(verbose_name="Active")

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        """Meta attributes."""

        model = ChangeSet
        fields = ("created", "deployment", "job_result", "record_count", "active")


class ChangeRecordTable(BaseTable):
    """Table for list view."""

    pk = tables.Column(linkify=True, verbose_name="ID")
    change_set = tables.Column(linkify=True)
    design_object_type = tables.Column(verbose_name="Design Object Type", accessor="_design_object_type")
    design_object = tables.Column(linkify=linkify_design_object, verbose_name="Design Object")
    full_control = BooleanColumn(verbose_name="Full Control")
    active = BooleanColumn(verbose_name="Active")

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        """Meta attributes."""

        model = ChangeRecord
        fields = ("pk", "change_set", "design_object_type", "design_object", "changes", "full_control", "active")
