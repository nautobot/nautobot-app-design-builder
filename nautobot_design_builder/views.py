"""UI Views for design builder."""

from django_tables2 import RequestConfig
from django.apps import apps as global_apps
from django.shortcuts import render

from rest_framework.decorators import action

from nautobot.core.views.mixins import (
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
    ObjectDestroyViewMixin,
)
from nautobot.apps.views import EnhancedPaginator, get_paginate_count
from nautobot.apps.models import count_related
from nautobot.core.views.generic import ObjectView
from nautobot.core.views.mixins import PERMISSIONS_ACTION_MAP

from nautobot_design_builder.api.serializers import (
    DesignSerializer,
    DeploymentSerializer,
    JournalSerializer,
    JournalEntrySerializer,
)
from nautobot_design_builder.filters import (
    DesignFilterSet,
    DeploymentFilterSet,
    JournalFilterSet,
    JournalEntryFilterSet,
)
from nautobot_design_builder.forms import (
    DesignFilterForm,
    DeploymentFilterForm,
    JournalFilterForm,
    JournalEntryFilterForm,
)
from nautobot_design_builder.models import Design, Deployment, Journal, JournalEntry
from nautobot_design_builder.tables import DesignTable, DeploymentTable, JournalTable, JournalEntryTable


PERMISSIONS_ACTION_MAP.update(
    {
        "docs": "view",
    }
)


class DesignUIViewSet(  # pylint:disable=abstract-method
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
    ObjectDestroyViewMixin,
):
    """UI views for the design model."""

    filterset_class = DesignFilterSet
    filterset_form_class = DesignFilterForm
    queryset = Design.objects.annotate(deployment_count=count_related(Deployment, "design"))
    serializer_class = DesignSerializer
    table_class = DesignTable
    action_buttons = ()
    lookup_field = "pk"

    def get_extra_context(self, request, instance=None):
        """Extend UI."""
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            deployments = Deployment.objects.restrict(request.user, "view").filter(design=instance)

            deployments_table = DeploymentTable(deployments)
            deployments_table.columns.hide("design")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(deployments_table)
            context["deployments_table"] = deployments_table
        return context

    @action(detail=True, methods=["get"])
    def docs(self, request, pk, *args, **kwargs):
        """Additional action to handle docs."""
        design = Design.objects.get(pk=pk)
        context = {
            "design_name": design.name,
            "is_modal": request.GET.get("modal"),
            "text_content": design.docs,
        }
        return render(request, "nautobot_design_builder/markdown_render.html", context)


class DeploymentUIViewSet(  # pylint:disable=abstract-method
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
    ObjectDestroyViewMixin,
):
    """UI views for the Deployment model."""

    filterset_class = DeploymentFilterSet
    filterset_form_class = DeploymentFilterForm
    queryset = Deployment.objects.all()
    serializer_class = DeploymentSerializer
    table_class = DeploymentTable
    action_buttons = ()
    lookup_field = "pk"
    verbose_name = "Design Deployment"
    verbose_name_plural = "Design Deployments"

    def get_extra_context(self, request, instance=None):
        """Extend UI."""
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            journals = (
                Journal.objects.restrict(request.user, "view")
                .filter(deployment=instance)
                .order_by("last_updated")
                .annotate(journal_entry_count=count_related(JournalEntry, "journal"))
            )

            journals_table = JournalTable(journals)
            journals_table.columns.hide("deployment")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(journals_table)
            context["journals_table"] = journals_table
        return context


class JournalUIViewSet(  # pylint:disable=abstract-method
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
            entries = JournalEntry.objects.restrict(request.user, "view").filter(journal=instance).order_by("-index")

            entries_table = JournalEntryTable(entries)
            entries_table.columns.hide("journal")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(entries_table)
            context["entries_table"] = entries_table
        return context


class JournalEntryUIViewSet(  # pylint:disable=abstract-method
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


class DesignProtectionObjectView(ObjectView):
    """View for the Audit Results tab dynamically generated on specific object detail views."""

    template_name = "nautobot_design_builder/designprotection_tab.html"

    def dispatch(self, request, *args, **kwargs):
        """Set the queryset for the given object and call the inherited dispatch method."""
        model = kwargs.pop("model")
        if not self.queryset:
            self.queryset = global_apps.get_model(model).objects.all()
        return super().dispatch(request, *args, **kwargs)

    def get_extra_context(self, request, instance):
        """Generate extra context for rendering the DesignProtection template."""
        content = {}

        journalentry_references = JournalEntry.objects.filter(
            _design_object_id=instance.id, active=True
        ).exclude_decommissioned()

        if journalentry_references:
            design_owner = journalentry_references.filter(full_control=True)
            if design_owner:
                content["object"] = design_owner.first().journal.deployment
            for journalentry in journalentry_references:
                for attribute in instance._meta.fields:
                    attribute_name = attribute.name
                    if attribute_name.startswith("_"):
                        continue
                    if (
                        attribute_name in journalentry.changes["differences"].get("added", {})
                        and journalentry.changes["differences"].get("added", {})[attribute_name]
                    ):
                        content[attribute_name] = journalentry.journal.deployment

        return {"active_tab": request.GET["tab"], "design_protection": content}
