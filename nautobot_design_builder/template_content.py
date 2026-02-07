"""Template content for nautobot_design_builder."""

from django.conf import settings
from django.utils.html import format_html
from nautobot.apps.templatetags import render_boolean
from nautobot.apps.ui import DataTablePanel, ObjectsTablePanel, SectionChoices, Tab, TemplateExtension
from nautobot.core.views.utils import get_obj_from_context
from nautobot.extras.utils import registry

from nautobot_design_builder.models import ChangeRecord, Deployment
from nautobot_design_builder.tables import DeploymentTable


def linkify(deployment):
    """Helper function to create an HTML link to a deployment."""
    return format_html(f'<a href="{deployment.get_absolute_url()}">{deployment}</a>')


def tab_factory(content_type_label):
    """Generate a Design Builder tab for a given content type."""

    class DesignBuilderTab(Tab):
        """Custom Tab class to conditionally render based on parent deployment existence."""

        def should_render(self, context):
            """Render the tab only if deployments exist for the object."""
            obj = get_obj_from_context(context)
            if Deployment.objects.filter(change_sets__records___design_object_id=obj.pk).exists():
                return super().should_render(context)
            return False

    class ParentDeploymentsTablePanel(ObjectsTablePanel):
        """DataTablePanel for displaying parent Deployments data."""

        def get_extra_context(self, context):
            obj = get_obj_from_context(context)
            parent_deployments = Deployment.objects.filter(change_sets__records___design_object_id=obj.pk).distinct()
            parent_deployments_table = DeploymentTable(parent_deployments)
            context.update({"parent_deployments": parent_deployments_table})
            return super().get_extra_context(context)

    class AffectedAttributesPanel(DataTablePanel):
        """ObjectsTablePanel for displaying affected attributes."""

        def get_extra_context(self, context):
            obj = get_obj_from_context(context)
            model = (obj._meta.app_label, obj._meta.model_name)
            protected = model in settings.PLUGINS_CONFIG["nautobot_design_builder"]["protected_models"]
            records = ChangeRecord.objects.filter(_design_object_id=obj.pk, active=True).exclude_decommissioned()
            affected_attributes = [
                {
                    "attribute": attribute,
                    "deployment": linkify(record.change_set.deployment),
                    "protected": render_boolean(protected),
                    "full_control": render_boolean(record.full_control),
                }
                for record in records
                for attribute in record.changes
            ]
            context.update({"affected_attributes": affected_attributes})
            return super().get_extra_context(context)

    class DesignBuilderExtension(TemplateExtension):  # pylint: disable=abstract-method
        """Dynamically generated DesignBuilderExtension class."""

        model = content_type_label

        object_detail_tabs = [
            DesignBuilderTab(
                weight=100,
                tab_id="design_builder_tab",
                label="Design Builder",
                panels=[
                    ParentDeploymentsTablePanel(
                        weight=100,
                        section=SectionChoices.FULL_WIDTH,
                        context_table_key="parent_deployments",
                        table_title="Design Deployments using this object",
                        paginate=True,
                    ),
                    AffectedAttributesPanel(
                        weight=200,
                        section=SectionChoices.FULL_WIDTH,
                        context_data_key="affected_attributes",
                        columns=["attribute", "deployment", "protected", "full_control"],
                        column_headers=["Attribute", "Controlling Design Deployment", "Protected", "Full Control"],
                    ),
                ],
            ),
        ]

    return DesignBuilderExtension


class DesignBuilderTemplateIterator:  # pylint: disable=too-few-public-methods
    """Iterator that generates ObjectsTablePanel classes for all objects beloging to a Design Deployment."""

    def __iter__(self):
        """Return a generator of ObjectsTablePanel classes for each registered model."""
        for app_label, models in registry["model_features"]["custom_validators"].items():
            for model in models:
                yield tab_factory(f"{app_label}.{model}")


template_extensions = DesignBuilderTemplateIterator()
