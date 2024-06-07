"""Import designs so they are discoverable by `load_jobs`."""

from .initial_data.jobs import InitialDesign
from .core_site.jobs import CoreSiteDesign
from .p2p.jobs import P2PDesign


__all__ = (
    "InitialDesign",
    "CoreSiteDesign",
    "P2PDesign",
)
