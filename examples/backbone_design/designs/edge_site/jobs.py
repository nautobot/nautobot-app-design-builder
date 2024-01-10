"""Basic design demonstrates the capabilities of the Design Builder."""
from nautobot.extras.jobs import StringVar, IPNetworkVar

from nautobot_design_builder.design_job import DesignJob

from .context import EdgeDesignContext


class EdgeDesign(DesignJob):
    """A basic design for design builder."""

    site_name = StringVar(label="Site Name", regex=r"\w{3}\d+")
    site_prefix = IPNetworkVar(label="Site Prefix")

    class Meta:
        """Metadata describing this design job."""

        name = "Edge Design"
        commit_default = False
        design_file = "designs/0001_design.yaml.j2"
        context_class = EdgeDesignContext
