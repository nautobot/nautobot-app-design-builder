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
    min_version = "1.6.0"
    max_version = "2.9999"
    default_settings = {}
    caching_config = {}

    # pylint: disable=no-self-argument
    @classproperty
    def context_repository(cls):
        """Retrieve the Git Repository slug that has been configured for the Design Builder."""
        return settings.PLUGINS_CONFIG[cls.name]["context_repository"]


config = NautobotDesignBuilderConfig  # pylint:disable=invalid-name
