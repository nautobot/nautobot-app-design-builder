"""Import designs so they are discoverable by `load_jobs`."""

from .initial_data.jobs import InitialDesign
from .core_site.jobs import CoreSiteDesign
from .l3vpn.jobs import L3vpnDesign
from .test.jobs import cestest


__all__ = (
    "InitialDesign",
    "CoreSiteDesign",
    "L3vpnDesign",
    "cestest",
)
