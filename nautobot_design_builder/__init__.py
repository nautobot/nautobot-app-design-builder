"""App declaration for nautobot_design_builder."""

# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

from nautobot.apps import NautobotAppConfig

__version__ = metadata.version(__name__)


class NautobotDesignBuilderConfig(NautobotAppConfig):
    """App configuration for the nautobot_design_builder app."""

    name = "nautobot_design_builder"
    verbose_name = "Nautobot Design Builder"
    version = __version__
    author = "Network to Code, LLC"
    description = "Nautobot app that uses design templates to easily create data objects in Nautobot with minimal input from a user."
    base_url = "design-builder"
    required_settings = []
    min_version = "2.0.0"
    max_version = "2.9999"
    default_settings = {}
    caching_config = {}
    docs_view_name = "plugins:nautobot_design_builder:docs"


config = NautobotDesignBuilderConfig  # pylint:disable=invalid-name
