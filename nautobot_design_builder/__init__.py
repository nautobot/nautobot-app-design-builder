"""App declaration for Nautobot Design Builder."""
from django.conf import settings
from django.utils.functional import classproperty

from nautobot.apps import NautobotAppConfig

import importlib_metadata as metadata

__version__ = metadata.version(__name__)


class DesignBuilderConfig(NautobotAppConfig):
    """App configuration for the nautobot_design_builder app."""

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

    def ready(self):
        super().ready()
        from . import signals  # noqa:F401 pylint:disable=import-outside-toplevel,unused-import,cyclic-import

    # pylint: disable=no-self-argument
    @classproperty
    def context_repository(cls):
        """Retrieve the Git Repository slug that has been configured for the Design Builder."""
        return settings.PLUGINS_CONFIG[cls.name]["context_repository"]


config = DesignBuilderConfig  # pylint:disable=invalid-name
