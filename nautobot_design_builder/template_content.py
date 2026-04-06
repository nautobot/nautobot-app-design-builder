"""Template content for nautobot_design_builder."""

from django.conf import settings
from nautobot.apps.templatetags import hyperlinked_object as hyperlink
from nautobot.apps.ui import (
    DataTablePanel,
    KeyValueTablePanel,
    ObjectsTablePanel,
    SectionChoices,
    Tab,
    TemplateExtension,
)
from nautobot.core.views.utils import get_obj_from_context
from nautobot.extras.utils import registry

from nautobot_design_builder.models import ChangeRecord, Deployment
from nautobot_design_builder.tables import DeploymentTable


class DesignBuilderTab(Tab):
    """Custom Tab class to conditionally render based on change record existence."""

    def should_render(self, context):
        """Render the tab only if change records exist for the object."""
        obj = get_obj_from_context(context)
        return ChangeRecord.objects.filter(_design_object_id=obj.pk, active=True).exclude_decommissioned().exists()


class DesignObjectFieldsPanel(KeyValueTablePanel):
    """Design-related fields for the object."""

    def should_render(self, context):
        """Only render if the object is part of an active change record."""
        obj = get_obj_from_context(context)
        model = (obj._meta.app_label, obj._meta.model_name)
        is_protected = model in settings.PLUGINS_CONFIG.get("nautobot_design_builder", {}).get("protected_models", [])
        full_control_records = ChangeRecord.objects.filter(_design_object_id=obj.pk, active=True, full_control=True)
        data = {
            "type": f"{obj._meta.app_label}.{obj._meta.model_name}",
            "protected": is_protected,
            "full_control": full_control_records.exists(),
        }
        if full_control_records.exists():
            data.update({"owner_deployment": hyperlink(full_control_records.first().change_set.deployment)})
        context.update({"data": data})
        return super().should_render(context)


class AffectedAttributesPanel(DataTablePanel):
    """ObjectsTablePanel for displaying affected attributes."""

    def get_extra_context(self, context):
        """Add affected attributes to the context."""
        obj = get_obj_from_context(context)
        records = (
            ChangeRecord.objects.filter(_design_object_id=obj.pk, active=True)
            .exclude_decommissioned()
            .select_related("change_set__deployment")
        )
        affected_set = {(attr, record.change_set.deployment) for record in records for attr in record.changes}
        affected_list = [{"attribute": attr, "deployment": hyperlink(deployment)} for attr, deployment in affected_set]
        context.update({"affected_attributes": affected_list})
        return super().get_extra_context(context)


class ParentDeploymentsTablePanel(ObjectsTablePanel):
    """DataTablePanel for displaying parent Deployments data."""

    def get_extra_context(self, context):
        """Add parent Deployments to the context."""
        obj = get_obj_from_context(context)
        parent_deployments = Deployment.objects.filter(change_sets__records___design_object_id=obj.pk).distinct()
        parent_deployments_table = DeploymentTable(parent_deployments)
        context.update({"parent_deployments": parent_deployments_table})
        return super().get_extra_context(context)


def tab_factory(content_type_label):
    """Generate a Design Builder tab for a given content type."""

    class DesignBuilderExtension(TemplateExtension):  # pylint: disable=abstract-method
        """Dynamically generated DesignBuilderExtension class."""

        model = content_type_label

        object_detail_tabs = [
            DesignBuilderTab(
                weight=100,
                tab_id="design_builder_tab",
                label="Design Builder",
                panels=[
                    DesignObjectFieldsPanel(
                        weight=100,
                        section=SectionChoices.LEFT_HALF,
                        label="Data Protection",
                        context_data_key="data",
                    ),
                    AffectedAttributesPanel(
                        weight=200,
                        section=SectionChoices.RIGHT_HALF,
                        context_data_key="affected_attributes",
                        columns=["attribute", "deployment"],
                        column_headers=["Attribute", "Controlling Design Deployment"],
                    ),
                    ParentDeploymentsTablePanel(
                        weight=300,
                        section=SectionChoices.FULL_WIDTH,
                        context_table_key="parent_deployments",
                        table_title="Design Deployments using this object",
                        paginate=True,
                    ),
                ],
            ),
        ]

    return DesignBuilderExtension


class DesignBuilderTemplateIterator:  # pylint: disable=too-few-public-methods
    """Iterator that generates ObjectsTablePanel classes for all objects belonging to a Design Deployment."""

    def __iter__(self):
        """Return a generator of ObjectsTablePanel classes for each registered model."""
        for app_label, models in registry.get("model_features", {}).get("custom_validators", {}).items():
            for model in models:
                yield tab_factory(f"{app_label}.{model}")


template_extensions = DesignBuilderTemplateIterator()
