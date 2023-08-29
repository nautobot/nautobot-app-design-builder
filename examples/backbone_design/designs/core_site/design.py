from nautobot.dcim.models import Region
from nautobot.extras.jobs import ObjectVar, StringVar, IPNetworkVar

from nautobot_design_builder.design_job import DesignJob

from .context import CoreSiteContext


class CoreSiteDesign(DesignJob):
    region = ObjectVar(
        label="Region",
        description="Region for the new backbone site",
        model=Region,
    )

    site_name = StringVar(regex=r"\w{3}\d+")

    site_prefix = IPNetworkVar(min_prefix_length=16, max_prefix_length=22)

    class Meta:
        name = "Backbone Site Design"
        commit_default = False
        design_file = "designs/0001_design.yaml.j2"
        context_class = CoreSiteContext
