"""Plugin declaration for my_plugin."""
# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

__version__ = metadata.version(__name__)

from nautobot.extras.plugins import NautobotAppConfig


class NautobotDesignBuilderConfig(NautobotAppConfig):
    """Plugin configuration for the my_plugin plugin."""

    name = "my_plugin"
    verbose_name = "Nautobot Design Builder"
    version = __version__
    author = "Network to Code, LLC"
    description = "Nautobot app that uses design templates to easily create data objects in Nautobot with minimal input from a user.."
    base_url = "design-builder"
    required_settings = []
    min_version = "1.6.8"
    max_version = "2.9999"
    default_settings = {}
    caching_config = {}


config = NautobotDesignBuilderConfig  # pylint:disable=invalid-name
