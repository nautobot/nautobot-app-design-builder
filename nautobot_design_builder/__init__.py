"""Plugin declaration for design_builder."""
from importlib import metadata

from django.conf import settings
from django.utils.functional import classproperty
from nautobot.extras.plugins import PluginConfig

__version__ = metadata.version(__name__)


class DesignBuilderConfig(PluginConfig):
    """Plugin configuration for the design_builder plugin."""

    name = "nautobot_design_builder"
    verbose_name = "Design Builder"
    version = __version__
    author = "Network to Code, LLC"
    description = "Design Builder."
    base_url = "nautobot-design-builder"
    required_settings = []
    min_version = "1.5.0"
    max_version = "2.9999"
    default_settings = {}
    caching_config = {}

    def ready(self):
        super().ready()
        from . import signals  # noqa:F401 pylint:disable=import-outside-toplevel,unused-import,cyclic-import

    # pylint: disable=no-self-argument
    @classproperty
    def context_repository(cls):
        """Retrieve the Git Repository slug that has been configured for the Design Builder."""
        return settings.PLUGINS_CONFIG[cls.name]["context_repository"]

    # pylint: disable=no-self-argument
    @classproperty
    def pre_decommission_hook(cls):
        """Retrieve the pre decommission hook callable for the Design Builder, if configured."""
        return settings.PLUGINS_CONFIG[cls.name].get("pre_decommission_hook", "")

    # pylint: disable=no-self-argument
    @classproperty
    def post_decommission_hook(cls):
        """Retrieve the post decommission hook callable for the Design Builder, if configured."""
        return settings.PLUGINS_CONFIG[cls.name].get("post_decommission_hook", "")


config = DesignBuilderConfig  # pylint:disable=invalid-name
