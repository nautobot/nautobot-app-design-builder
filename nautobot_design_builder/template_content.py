"""Template content for nautobot_design_builder."""

from nautobot.apps.ui import DataTablePanel, ObjectsTablePanel, SectionChoices, Tab, TemplateExtension
from nautobot.core.views.utils import get_obj_from_context
from nautobot.extras.utils import registry

from nautobot_design_builder.models import ChangeRecord, Deployment
from nautobot_design_builder.tables import DeploymentTable


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

    class ProtectedAttributesPanel(DataTablePanel):
        """ObjectsTablePanel for displaying protected attributes."""

        def get_extra_context(self, context):
            obj = get_obj_from_context(context)
            protected_attributes = [
                {"attribute": attribute, "deployment": deployment}
                for deployment in Deployment.objects.filter(change_sets__records___design_object_id=obj.pk).distinct()
                for record in ChangeRecord.objects.filter(
                    _design_object_id=obj.pk, active=True, change_set__deployment=deployment
                ).exclude_decommissioned()
                for attribute in record.changes
            ]
            context.update({"protected_attributes": protected_attributes})
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
                    ProtectedAttributesPanel(
                        weight=200,
                        section=SectionChoices.FULL_WIDTH,
                        context_data_key="protected_attributes",
                        columns=["attribute", "deployment"],
                        column_headers=["Protected Attribute", "Controlling Deployment"],
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
