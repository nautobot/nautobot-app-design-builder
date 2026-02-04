"""Template content for nautobot_design_builder."""

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from nautobot.apps.ui import ObjectsTablePanel, SectionChoices, Tab, TemplateExtension
from nautobot.core.views.utils import get_obj_from_context
from nautobot.extras.utils import registry

from nautobot_design_builder.models import ChangeRecord, Deployment
from nautobot_design_builder.tables import DeploymentTable


class DeploymentObjectsTablePanel(ObjectsTablePanel):
    """DataTablePanel for displaying Deployment data."""

    def should_render(self, context):
        """Determine if the panel should be rendered based on the presence of data in context."""
        obj = get_obj_from_context(context)
        parent_deployments = Deployment.objects.filter(change_sets__records___design_object_id=obj.pk).distinct()
        parent_deployments_table = DeploymentTable(parent_deployments)
        context.update({"parent_deployments": parent_deployments_table})
        # return bool(parent_deployments)
        return True


def tab_factory(content_type_label):
    """Generate a Design Builder tab for a given content type."""

    class DesignBuilderTab(TemplateExtension):  # pylint: disable=W0223
        """Dynamically generated DesignBuilderTab class."""

        model = content_type_label

        object_detail_tabs = [
            Tab(
                weight=100,
                tab_id="design_builder_tab",
                label="Design Builder",
                panels=[
                    DeploymentObjectsTablePanel(
                        weight=100,
                        section=SectionChoices.FULL_WIDTH,
                        context_table_key="parent_deployments",
                        table_title="Design Deployments containing this object",
                        max_display_count=10,
                        paginate=True,
                    ),
                ],
            ),
        ]

    return DesignBuilderTab


# def tab_factory(content_type_label):
#     """Generate a DataComplianceTab object for a given content type."""

#     class DesignProtectionTab(TemplateExtension):  # pylint: disable=W0223
#         """Dynamically generated DesignProtectionTab class."""

#         model = content_type_label

#         def detail_tabs(self):
#             return [
#                 {
#                     "title": "Design Protection",
#                     "url": reverse(
#                         "plugins:nautobot_design_builder:design-protection-tab",
#                         kwargs={"id": self.context["object"].id, "model": self.model},
#                     ),
#                 },
#             ]

#     return DesignProtectionTab


class DesignBuilderTemplateIterator:  # pylint: disable=too-few-public-methods
    """Iterator that generates ObjectsTablePanel classes for all objects beloging to a Design Deployment."""

    def __iter__(self):
        """Return a generator of ObjectsTablePanel classes for each registered model."""
        for app_label, models in registry["model_features"]["custom_validators"].items():
            for model in models:
                yield tab_factory(f"{app_label}.{model}")
                # if (app_label, model) in settings.PLUGINS_CONFIG["nautobot_design_builder"]["protected_models"]:
                #     yield tab_factory(f"{app_label}.{model}")


template_extensions = DesignBuilderTemplateIterator()
