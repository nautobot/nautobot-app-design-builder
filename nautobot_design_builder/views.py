"""UI Views for design builder."""
from django_tables2 import RequestConfig
from nautobot.core.views.mixins import (
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
    ObjectDestroyViewMixin,
    ObjectBulkDestroyViewMixin,
)
from rest_framework.response import Response
from rest_framework import status
from nautobot.core.views import generic
from django.shortcuts import redirect
from django.urls import reverse
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.utils import count_related
from django.core.exceptions import ValidationError
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
from nautobot_design_builder import choices


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


from rest_framework.exceptions import ValidationError


class DesignInstanceBulkDestroy(ObjectBulkDestroyViewMixin):
    def perform_bulk_destroy(self, request, **kwargs):
        self.pk_list = request.POST.getlist("pk")
        instances = self.get_queryset().filter(pk__in=self.pk_list)

        # TODO: find how to provide proper exception
        instances_not_ready = []
        for instance in instances:
            if not (
                instance.status.name == choices.DesignInstanceStatusChoices.DECOMMISSIONED
                and instance.oper_status.name
                in [choices.DesignInstanceOperStatusChoices.PENDING, choices.DesignInstanceOperStatusChoices.ROLLBACKED]
            ):
                instances_not_ready.append(instance)
        if instances_not_ready:
            raise ValidationError(["errp1", "errpr"])
            # return Response(
            #     {"Error": f"Instances {[instance.name for instance in instances_not_ready]} can't be deleted."},
            #     status=status.HTTP_400_BAD_REQUEST,
            # )
        return super(DesignInstanceBulkDestroy, self).perform_bulk_destroy(request, **kwargs)


class DesignInstanceUIViewSet(
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
    ObjectDestroyViewMixin,
    DesignInstanceBulkDestroy,
):
    """UI views for the design instance model."""

    filterset_class = DesignInstanceFilterSet
    filterset_form_class = DesignInstanceFilterForm
    queryset = DesignInstance.objects.all()
    serializer_class = DesignInstanceSerializer
    table_class = DesignInstanceTable
    action_buttons = ("delete",)
    lookup_field = "pk"

    def get_extra_context(self, request, instance=None):
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


# class DecommissionJobView(generic.ObjectView):
#     """Special View to trigger the Job."""

#     queryset = DesignInstance.objects.all()

#     def get(self, request, *args, **kwargs):
#         """Custom GET to run a the Job."""
#         class_path = "plugins/nautobot_design_builder.jobs/DesignInstanceDecommissioning"
#         # TODO: how to pass data to the Job to run
#         data = {"design_instances": [str(kwargs["pk"])]}
#         print(data)
#         return redirect(
#             reverse(
#                 "extras:job",
#                 kwargs={
#                     "class_path": class_path,
#                 },
#             )
#             + "?_commit=False",
#         )


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
