"""Tables for design builder."""

from django_tables2 import Column
from django_tables2.utils import Accessor
from nautobot.apps.tables import StatusTableMixin, BaseTable
from nautobot.apps.tables import BooleanColumn, ColoredLabelColumn, ButtonsColumn

from nautobot_design_builder.models import Design, Deployment, Journal, JournalEntry

DESIGNTABLE = """

<a value="{% url 'plugins:nautobot_design_builder:design_docs' pk=record.pk %}" class="openBtn" data-href="{% url 'plugins:nautobot_design_builder:design_docs' pk=record.pk %}?modal=true">
    <i class="mdi mdi-file-document-outline" title="Design Documentation"></i>
</a>
<a href="{% url 'extras:job_run_by_class_path' class_path=record.job.class_path %}" class="btn btn-xs btn-primary" title="Trigger Design Creation">
    <i class="mdi mdi-play" title="Deploy Design"></i>
</a>
<a href="{% url 'extras:job_edit' pk=record.job.pk %}" class="btn btn-xs btn-warning" title="Edit Design Job">
    <i class="mdi mdi-pencil"></i>
</a>
"""


class DesignTable(BaseTable):
    """Table for list view."""

    name = Column(linkify=True)
    instance_count = Column(linkify=True, accessor=Accessor("deployment_count"), verbose_name="Deployments")
    actions = ButtonsColumn(Design, buttons=("changelog", "delete"), prepend_template=DESIGNTABLE)
    job_last_synced = Column(accessor="job.last_updated", verbose_name="Last Synced Time")

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        """Meta attributes."""

        model = Design
        fields = ("name", "version", "job_last_synced", "description", "instance_count")


DEPLOYMENT_TABLE = """
{% load utils %}
<a href="{% url "extras:job_run_by_class_path" class_path="nautobot_design_builder.jobs.DeploymentDecommissioning" %}?deployments={{record.pk}}" class="btn btn-xs btn-primary" title="Decommission">
    <i class="mdi mdi-delete-sweep"></i>
</a>
<a href="{% url 'extras:job_run' pk=record.design.job.pk %}?kwargs_from_job_result={% with record|get_last_journal as last_journal %}{{ last_journal.job_result.pk }}{% endwith %}"
    class="btn btn-xs btn-success" title="Re-run job with same arguments.">
    <i class="mdi mdi-repeat"></i>
</a>
"""


class DeploymentTable(StatusTableMixin, BaseTable):
    """Table for list view."""

    name = Column(linkify=True)
    design = Column(linkify=True)
    first_implemented = Column(verbose_name="Deployment Time")
    last_implemented = Column(verbose_name="Last Update Time")
    created_by = Column(verbose_name="Deployed by")
    last_updated_by = Column(verbose_name="Last Updated by")
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


class JournalTable(BaseTable):
    """Table for list view."""

    pk = Column(linkify=True, verbose_name="ID")
    design_instance = Column(linkify=True, verbose_name="Deployment")
    job_result = Column(accessor=Accessor("job_result.created"), linkify=True, verbose_name="Design Job Result")
    journal_entry_count = Column(accessor=Accessor("journal_entry_count"), verbose_name="Journal Entries")
    active = BooleanColumn(verbose_name="Active Journal")

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        """Meta attributes."""

        model = Journal
        fields = ("pk", "design_instance", "job_result", "journal_entry_count", "active")


class JournalEntryTable(BaseTable):
    """Table for list view."""

    pk = Column(linkify=True, verbose_name="ID")
    journal = Column(linkify=True)
    design_object = Column(linkify=True, verbose_name="Design Object")
    full_control = BooleanColumn(verbose_name="Full Control")
    active = BooleanColumn(verbose_name="Active")

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        """Meta attributes."""

        model = JournalEntry
        fields = ("pk", "journal", "design_object", "changes", "full_control", "active")
