"""Import designs so they are discoverable by `load_jobs`."""

from .initial_data.jobs import InitialDesign, InitialDesignV2
from .core_site.jobs import CoreSiteDesign
from .edge_site.jobs import EdgeDesign

__all__ = (
    "InitialDesign",
    "InitialDesignV2",
    "CoreSiteDesign",
    "EdgeDesign",
)
