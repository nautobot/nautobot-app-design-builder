"""Tables for design builder."""
from django_tables2 import Column
from django_tables2.utils import Accessor
from nautobot.apps.tables import StatusTableMixin, BaseTable
from nautobot.utilities.tables import BooleanColumn

from design_builder.models import Design, DesignInstance, Journal, JournalEntry


class DesignTable(StatusTableMixin, BaseTable):
    """Table for list view."""

    job = Column(linkify=True)
    name = Column(linkify=True)
    instance_count = Column(accessor=Accessor("instance_count"), verbose_name="Instances")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = Design
        fields = ("name", "job", "instance_count", "status")


class DesignInstanceTable(BaseTable):
    """Table for list view."""

    name = Column(linkify=True)
    design = Column(linkify=True)

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = DesignInstance
        fields = ("name", "design", "owner", "first_implemented", "last_implemented")


class JournalTable(BaseTable):
    """Table for list view."""

    pk = Column(linkify=True, verbose_name="ID")
    design_instance = Column(linkify=True)
    job_result = Column(linkify=True)
    journal_entry_count = Column(accessor=Accessor("journal_entry_count"), verbose_name="Journal Entries")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = Journal
        fields = ("pk", "design_instance", "job_result", "journal_entry_count")


class JournalEntryTable(BaseTable):
    """Table for list view."""

    pk = Column(linkify=True, verbose_name="ID")
    journal = Column(linkify=True)
    design_object = Column(linkify=True, verbose_name="Design Object")
    full_control = BooleanColumn(verbose_name="Full Control")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = JournalEntry
        fields = ("pk", "journal", "design_object", "changes", "full_control")
