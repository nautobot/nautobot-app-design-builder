"""Plugin declaration for design_builder."""
from django.conf import settings
from django.utils.functional import classproperty

from nautobot.apps import NautobotAppConfig

# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
try:
    from importlib import metadata
except ImportError:
    # Python version < 3.8
    import importlib_metadata as metadata

__version__ = metadata.version(__name__)


class DesignBuilderConfig(NautobotAppConfig):
    """Plugin configuration for the design_builder plugin."""

    name = "nautobot_design_builder"
    verbose_name = "Design Builder"
    version = __version__
    author = "Network to Code, LLC"
    description = "Design Builder."
    base_url = "design-builder"
    required_settings = []
    min_version = "1.6.0"
    max_version = "2.9999"
    default_settings = {}
    caching_config = {}

    # pylint: disable=no-self-argument
    @classproperty
    def context_repository(cls):
        """Retrieve the Git Repository slug that has been configured for the Design Builder."""
        return settings.PLUGINS_CONFIG[cls.name]["context_repository"]


config = DesignBuilderConfig  # pylint:disable=invalid-name
