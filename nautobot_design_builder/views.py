"""UI Views for design builder."""
from django_tables2 import RequestConfig
from nautobot.core.views.mixins import (
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
    ObjectDestroyViewMixin,
)
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.utils import count_related

from nautobot_design_builder.api.serializers import (
    DesignSerializer,
    DesignInstanceSerializer,
    JournalSerializer,
    JournalEntrySerializer,
)
from nautobot_design_builder.filters import (
    DesignFilterSet,
    DesignInstanceFilterSet,
    JournalFilterSet,
    JournalEntryFilterSet,
)
from nautobot_design_builder.forms import (
    DesignFilterForm,
    DesignInstanceFilterForm,
    JournalFilterForm,
    JournalEntryFilterForm,
)
from nautobot_design_builder.models import Design, DesignInstance, Journal, JournalEntry
from nautobot_design_builder.tables import DesignTable, DesignInstanceTable, JournalTable, JournalEntryTable


class DesignUIViewSet(
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
):
    """UI views for the design model."""

    filterset_class = DesignFilterSet
    filterset_form_class = DesignFilterForm
    queryset = Design.objects.annotate(instance_count=count_related(DesignInstance, "design"))
    serializer_class = DesignSerializer
    table_class = DesignTable
    action_buttons = ()
    lookup_field = "pk"

    def get_extra_context(self, request, instance=None):
        """Extend UI."""
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            design_instances = DesignInstance.objects.restrict(request.user, "view").filter(design=instance)

            instances_table = DesignInstanceTable(design_instances)
            instances_table.columns.hide("design")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(instances_table)
            context["instances_table"] = instances_table
        return context


class DesignInstanceUIViewSet(
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
    ObjectDestroyViewMixin,
):
    """UI views for the design instance model."""

    filterset_class = DesignInstanceFilterSet
    filterset_form_class = DesignInstanceFilterForm
    queryset = DesignInstance.objects.all()
    serializer_class = DesignInstanceSerializer
    table_class = DesignInstanceTable
    action_buttons = ()
    lookup_field = "pk"

    def get_extra_context(self, request, instance=None):
        """Extend UI."""
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            journals = Journal.objects.restrict(request.user, "view").filter(design_instance=instance)

            journals_table = JournalTable(journals)
            journals_table.columns.hide("design_instance")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(journals_table)
            context["journals_table"] = journals_table
        return context


class JournalUIViewSet(
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
):
    """UI views for the journal model."""

    filterset_class = JournalFilterSet
    filterset_form_class = JournalFilterForm
    queryset = Journal.objects.annotate(journal_entry_count=count_related(JournalEntry, "journal"))
    serializer_class = JournalSerializer
    table_class = JournalTable
    action_buttons = ()
    lookup_field = "pk"

    def get_extra_context(self, request, instance=None):
        """Extend UI."""
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            entries = JournalEntry.objects.restrict(request.user, "view").filter(journal=instance)

            entries_table = JournalEntryTable(entries)
            entries_table.columns.hide("journal")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(entries_table)
            context["entries_table"] = entries_table
        return context


class JournalEntryUIViewSet(
    ObjectDetailViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
):
    """UI views for the journal entry model."""

    filterset_class = JournalEntryFilterSet
    filterset_form_class = JournalEntryFilterForm
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer
    table_class = JournalEntryTable
    action_buttons = ()
    lookup_field = "pk"
