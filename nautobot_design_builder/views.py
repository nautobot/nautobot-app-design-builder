"""UI Views for design builder."""

from django_tables2 import RequestConfig
from django.apps import apps as global_apps
from django.shortcuts import render
from django.core.exceptions import FieldDoesNotExist

from rest_framework.decorators import action

from nautobot.core.views.mixins import (
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
    ObjectDestroyViewMixin,
)
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.utils import count_related
from nautobot.core.views.generic import ObjectView
from nautobot.core.views.mixins import PERMISSIONS_ACTION_MAP

from nautobot_design_builder import choices
from nautobot_design_builder.api.serializers import (
    DesignSerializer,
    DeploymentSerializer,
    ChangeSetSerializer,
    ChangeRecordSerializer,
)
from nautobot_design_builder.filters import (
    DesignFilterSet,
    DeploymentFilterSet,
    ChangeSetFilterSet,
    ChangeRecordFilterSet,
)
from nautobot_design_builder.forms import (
    DesignFilterForm,
    DeploymentFilterForm,
    ChangeSetFilterForm,
    ChangeRecordFilterForm,
)
from nautobot_design_builder.models import Design, Deployment, ChangeSet, ChangeRecord
from nautobot_design_builder.tables import (
    DesignObjectsTable,
    DesignTable,
    DeploymentTable,
    ChangeSetTable,
    ChangeRecordTable,
)


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
            context["is_deployment"] = instance.design_mode == choices.DesignModeChoices.DEPLOYMENT
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
    """UI views for the design instance model."""

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
            change_sets = (
                ChangeSet.objects.restrict(request.user, "view")
                .filter(deployment=instance)
                .order_by("last_updated")
                .annotate(record_count=count_related(ChangeRecord, "change_set"))
            )

            change_sets_table = ChangeSetTable(change_sets)
            change_sets_table.columns.hide("deployment")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(change_sets_table)
            context["change_sets_table"] = change_sets_table

            design_objects = ChangeRecord.objects.restrict(request.user, "view").design_objects(instance)
            design_objects_table = DesignObjectsTable(design_objects)
            context["design_objects_table"] = design_objects_table
        return context


class ChangeSetUIViewSet(  # pylint:disable=abstract-method
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
):
    """UI views for the ChangeSet model."""

    filterset_class = ChangeSetFilterSet
    filterset_form_class = ChangeSetFilterForm
    queryset = ChangeSet.objects.annotate(record_count=count_related(ChangeRecord, "change_set"))
    serializer_class = ChangeSetSerializer
    table_class = ChangeSetTable
    action_buttons = ()
    lookup_field = "pk"

    def get_extra_context(self, request, instance=None):
        """Extend UI."""
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            records = (
                ChangeRecord.objects.restrict(request.user, "view")
                .filter(active=True, change_set=instance)
                .order_by("-index")
            )

            records_table = ChangeRecordTable(records)
            records_table.columns.hide("change_set")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(records_table)
            context["records_table"] = records_table
        return context


class ChangeRecordUIViewSet(  # pylint:disable=abstract-method
    ObjectDetailViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
):
    """UI views for the ChangeRecord model."""

    filterset_class = ChangeRecordFilterSet
    filterset_form_class = ChangeRecordFilterForm
    queryset = ChangeRecord.objects.all()
    serializer_class = ChangeRecordSerializer
    table_class = ChangeRecordTable
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

        records = ChangeRecord.objects.filter(_design_object_id=instance.id, active=True).exclude_decommissioned()

        if records:
            design_owner = records.filter(full_control=True, _design_object_id=instance.pk)
            if design_owner:
                content["object"] = design_owner.first().change_set.deployment
            for record in records:
                for attribute in record.changes:
                    try:
                        field = instance._meta.get_field(attribute)
                        content[field.name] = record.change_set.deployment
                    except FieldDoesNotExist:
                        # TODO: should this be logged? I can't think of when we would care
                        # that a model's fields have changed since a design was implemented
                        pass

        return {"active_tab": request.GET["tab"], "design_protection": content}
