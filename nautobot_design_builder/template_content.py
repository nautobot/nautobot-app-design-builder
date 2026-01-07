"""Template content for nautobot_design_builder."""

from django.conf import settings
from django.urls import reverse
from nautobot.extras.plugins import TemplateExtension
from nautobot.extras.utils import registry


def tab_factory(content_type_label):
    """Generate a DataComplianceTab object for a given content type."""

    class DesignProtectionTab(TemplateExtension):  # pylint: disable=W0223
        """Dynamically generated DesignProtectionTab class."""

        model = content_type_label

        def detail_tabs(self):
            return [
                {
                    "title": "Design Protection",
                    "url": reverse(
                        "plugins:nautobot_design_builder:design-protection-tab",
                        kwargs={"id": self.context["object"].id, "model": self.model},
                    ),
                },
            ]

    return DesignProtectionTab


class DesignBuilderTemplateIterator:  # pylint: disable=too-few-public-methods
    """Iterator that generates CustomValidator classes for each model registered in the extras feature query registry 'custom_validators'."""

    def __iter__(self):
        """Return a generator of CustomValidator classes for each registered model."""
        for app_label, models in registry["model_features"]["custom_validators"].items():
            for model in models:
                if (app_label, model) in settings.PLUGINS_CONFIG["nautobot_design_builder"]["protected_models"]:
                    label = f"{app_label}.{model}"
                    yield tab_factory(label)


template_extensions = DesignBuilderTemplateIterator()
