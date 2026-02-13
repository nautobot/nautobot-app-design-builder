"""Plugin declaration for nautobot_design_builder."""

# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

from django.conf import settings
from django.utils.functional import classproperty

__version__ = metadata.version(__name__)

from nautobot.extras.plugins import NautobotAppConfig


class NautobotDesignBuilderConfig(NautobotAppConfig):
    """Plugin configuration for the nautobot_design_builder plugin."""

    name = "nautobot_design_builder"
    verbose_name = "Nautobot Design Builder"
    version = __version__
    author = "Network to Code, LLC"
    description = "Nautobot app that uses design templates to easily create data objects in Nautobot with minimal input from a user.."
    base_url = "design-builder"
    required_settings = []
    default_settings = {
        "protected_models": [],
        "protected_superuser_bypass": True,
    }
    docs_view_name = "plugins:nautobot_design_builder:docs"
    searchable_models = ["design"]

    def ready(self):
        """Callback after design builder is loaded."""
        super().ready()
        from . import signals  # noqa:F401 pylint:disable=import-outside-toplevel,unused-import,cyclic-import

    # pylint: disable=no-self-argument
    @classproperty
    def context_repository(cls):
        """Retrieve the Git Repository slug that has been configured for the Design Builder."""
        return settings.PLUGINS_CONFIG[cls.name]["context_repository"]


config = NautobotDesignBuilderConfig  # pylint:disable=invalid-name
