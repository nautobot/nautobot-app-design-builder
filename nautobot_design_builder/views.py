"""UI Views for design builder."""

from django.apps import apps as global_apps
from django.core.exceptions import FieldDoesNotExist
from django.shortcuts import render
from nautobot.apps.models import count_related
from nautobot.apps.ui import ObjectDetailContent, ObjectFieldsPanel, ObjectsTablePanel, ObjectTextPanel, SectionChoices
from nautobot.apps.views import get_obj_from_context
from nautobot.core.views.generic import ObjectView
from nautobot.core.views.mixins import (
    PERMISSIONS_ACTION_MAP,
    ObjectChangeLogViewMixin,
    ObjectDestroyViewMixin,
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectNotesViewMixin,
)
from rest_framework.decorators import action

from nautobot_design_builder import choices, models, tables
from nautobot_design_builder.api.serializers import (
    ChangeRecordSerializer,
    ChangeSetSerializer,
    DeploymentSerializer,
    DesignSerializer,
)
from nautobot_design_builder.filters import (
    ChangeRecordFilterSet,
    ChangeSetFilterSet,
    DeploymentFilterSet,
    DesignFilterSet,
)
from nautobot_design_builder.forms import (
    ChangeRecordFilterForm,
    ChangeSetFilterForm,
    DeploymentFilterForm,
    DesignFilterForm,
)

PERMISSIONS_ACTION_MAP.update(
    {
        "docs": "view",
    }
)


class DesignDeploymentTablePanel(ObjectsTablePanel):
    """Custom panel to show the Design associated with a Deployment."""

    def should_render(self, context):
        """Only render if the Design instance has design_mode of deployment."""
        if not super().should_render(context):
            return False
        instance = get_obj_from_context(context)
        return instance.design_mode == choices.DesignModeChoices.DEPLOYMENT


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
    queryset = models.Design.objects.annotate(deployment_count=count_related(models.Deployment, "design"))
    serializer_class = DesignSerializer
    table_class = tables.DesignTable
    action_buttons = ()
    lookup_field = "pk"

    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=[
                    "job",
                    "job__last_updated",
                    "version",
                    "description",
                    "design_mode",
                ],
                value_transforms={
                    # Transform the design_mode field to its Human readable form, can be None if the Job has not loaded.
                    "design_mode": [lambda value: choices.DesignModeChoices.as_dict()[value] if value else None],
                },
                key_transforms={
                    "job__last_updated": "Job Last Synced",
                },
            ),
            ObjectTextPanel(
                section=SectionChoices.RIGHT_HALF,
                weight=200,
                label="Documentation",
                object_field="docs",
                render_as=ObjectTextPanel.RenderOptions.MARKDOWN,
            ),
            DesignDeploymentTablePanel(
                weight=300,
                section=SectionChoices.FULL_WIDTH,
                table_class=tables.DeploymentTable,
                table_filter="design",
                related_field_name="design",
                enable_bulk_actions=False,
                exclude_columns=["design"],
                include_paginator=True,
            ),
        ),
    )

    @action(detail=True, methods=["get"])
    def docs(self, request, pk, *args, **kwargs):
        """Additional action to handle docs."""
        design = models.Design.objects.get(pk=pk)
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
    queryset = models.Deployment.objects.all()
    serializer_class = DeploymentSerializer
    table_class = tables.DeploymentTable
    action_buttons = ()
    lookup_field = "pk"
    verbose_name = "Design Deployment"
    verbose_name_plural = "Design Deployments"

    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=[
                    "name",
                    "version",
                    "created_by",
                    "first_implemented",
                    "last_updated_by",
                    "last_implemented",
                    "design",
                    "status",
                ],
                key_transforms={
                    "created_by": "Deployed by",
                    "first_implemented": "Deployment Time",
                    "last_implemented": "Last Update Time",
                },
            ),
            ObjectsTablePanel(
                section=SectionChoices.RIGHT_HALF,
                weight=200,
                table_title="ChangeSets",
                context_table_key="change_sets_table",
                related_field_name="deployment",
                enable_bulk_actions=False,
                exclude_columns=["deployment"],
                include_paginator=True,
            ),
            ObjectsTablePanel(
                weight=300,
                section=SectionChoices.FULL_WIDTH,
                table_title="Design Objects",
                context_table_key="design_objects_table",
                related_field_name="deployment",
                enable_bulk_actions=False,
                include_paginator=True,
            ),
        ),
    )

    def get_extra_context(self, request, instance=None):
        """Extend UI."""
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            change_sets = (
                models.ChangeSet.objects.restrict(request.user, "view")
                .filter(deployment=instance)
                .order_by("last_updated")
                .annotate(record_count=count_related(models.ChangeRecord, "change_set"))
            )
            change_sets_table = tables.ChangeSetTable(change_sets)
            context["change_sets_table"] = change_sets_table

            design_objects = models.ChangeRecord.objects.restrict(request.user, "view").design_objects(instance)
            design_objects_table = tables.DesignObjectsTable(design_objects)
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
    queryset = models.ChangeSet.objects.annotate(record_count=count_related(models.ChangeRecord, "change_set"))
    serializer_class = ChangeSetSerializer
    table_class = tables.ChangeSetTable
    action_buttons = ()
    lookup_field = "pk"

    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                label="Journal",
                fields=[
                    "job_result",
                    "deployment",
                    "active",
                ],
            ),
            ObjectsTablePanel(
                weight=200,
                section=SectionChoices.FULL_WIDTH,
                label="Change Records",
                context_table_key="records_table",
                related_field_name="change_set",
                enable_bulk_actions=False,
                include_paginator=True,
                exclude_columns=["change_set"],
            ),
        ),
    )

    def get_extra_context(self, request, instance=None):
        """Extend UI."""
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            records = (
                models.ChangeRecord.objects.restrict(request.user, "view")
                .filter(active=True, change_set=instance)
                .order_by("-index")
            )

            records_table = tables.ChangeRecordTable(records)
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
    queryset = models.ChangeRecord.objects.all()
    serializer_class = ChangeRecordSerializer
    table_class = tables.ChangeRecordTable
    action_buttons = ()
    lookup_field = "pk"

    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=[
                    "design_object",
                    "change_set",
                    "full_control",
                    "last_updated",
                ],
            ),
            ObjectTextPanel(
                section=SectionChoices.RIGHT_HALF,
                weight=200,
                label="Changes",
                object_field="changes",
                render_as=ObjectTextPanel.RenderOptions.JSON,
            ),
        ),
    )


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

        records = models.ChangeRecord.objects.filter(
            _design_object_id=instance.id, active=True
        ).exclude_decommissioned()

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
