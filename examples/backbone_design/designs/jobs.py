"""Import designs so they are discoverable by `load_jobs`."""

from .initial_data.jobs import InitialDesign
from .core_site.jobs import CoreSiteDesign
from .edge_site.jobs import EdgeDesign

__all__ = (
    "InitialDesign",
    "CoreSiteDesign",
    "EdgeDesign",
)
