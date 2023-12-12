"""Tables for design builder."""
from django_tables2 import Column
from django_tables2.utils import Accessor
from nautobot.apps.tables import StatusTableMixin, BaseTable
from nautobot.utilities.tables import BooleanColumn, ColoredLabelColumn, ButtonsColumn

from nautobot_design_builder.models import Design, DesignInstance, Journal, JournalEntry


DESIGNTABLE = """
<a href="{% url 'extras:job' class_path=record.job.class_path %}" class="btn btn-xs btn-primary" title="Trigger Design Creation">
    <i class="mdi mdi-arrow-right-drop-circle-outline"></i>
</a>
"""


class DesignTable(BaseTable):
    """Table for list view."""

    job = Column(linkify=True)
    name = Column(linkify=True)
    instance_count = Column(linkify=True, accessor=Accessor("instance_count"), verbose_name="Instances")
    actions = ButtonsColumn(Design, buttons=("changelog",), prepend_template=DESIGNTABLE)

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        """Meta attributes."""

        model = Design
        fields = ("name", "job", "instance_count")


DESIGNINSTANCETABLE = """
<a href="{% url "extras:job" class_path="plugins/nautobot_design_builder.jobs/DesignInstanceDecommissioning" %}?design_instances={{record.pk}}" class="btn btn-xs btn-primary" title="Decommission">
    <i class="mdi mdi-delete-sweep"></i>
</a>
"""


class DesignInstanceTable(StatusTableMixin, BaseTable):
    """Table for list view."""

    name = Column(linkify=True)
    design = Column(linkify=True)
    live_state = ColoredLabelColumn()
    actions = ButtonsColumn(
        DesignInstance,
        buttons=(
            "delete",
            "changelog",
        ),
        prepend_template=DESIGNINSTANCETABLE,
    )

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        """Meta attributes."""

        model = DesignInstance
        fields = ("name", "design", "owner", "first_implemented", "last_implemented", "status", "live_state")


class JournalTable(BaseTable):
    """Table for list view."""

    pk = Column(linkify=True, verbose_name="ID")
    design_instance = Column(linkify=True)
    job_result = Column(linkify=True)
    journal_entry_count = Column(accessor=Accessor("journal_entry_count"), verbose_name="Journal Entries")

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        """Meta attributes."""

        model = Journal
        fields = ("pk", "design_instance", "job_result", "journal_entry_count")


class JournalEntryTable(BaseTable):
    """Table for list view."""

    pk = Column(linkify=True, verbose_name="ID")
    journal = Column(linkify=True)
    design_object = Column(linkify=True, verbose_name="Design Object")
    full_control = BooleanColumn(verbose_name="Full Control")

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        """Meta attributes."""

        model = JournalEntry
        fields = ("pk", "journal", "design_object", "changes", "full_control")
