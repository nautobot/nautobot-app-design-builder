"""Design to create a core backbone site."""
from nautobot.dcim.models import Location

from nautobot.extras.jobs import ObjectVar, StringVar, IPNetworkVar

from nautobot_design_builder.design_job import DesignJob

from .context import CoreSiteContext


class CoreSiteDesign(DesignJob):
    """Create a core backbone site."""

    region = ObjectVar(
        label="Region",
        description="Region for the new backbone site",
        model=Location,
    )

    site_name = StringVar(regex=r"\w{3}\d+")

    site_prefix = IPNetworkVar(min_prefix_length=16, max_prefix_length=22)

    class Meta:
        """Metadata needed to implement the backbone site design."""

        name = "Backbone Site Design"
        commit_default = False
        design_file = "designs/0001_design.yaml.j2"
        context_class = CoreSiteContext
        nautobot_version = ">=2"
