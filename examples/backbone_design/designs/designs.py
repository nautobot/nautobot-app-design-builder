"""Import designs so they are discoverable by `load_jobs`."""

from .initial_data.design import InitialDesign
from .core_site.design import CoreSiteDesign

__all__ = (
    "InitialDesign",
    "CoreSiteDesign",
)
