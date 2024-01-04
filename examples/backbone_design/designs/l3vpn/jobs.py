"""Design to create a l3vpn site."""
from django.core.exceptions import ValidationError

from nautobot.dcim.models import Device
from nautobot.extras.jobs import ObjectVar, StringVar

from nautobot_design_builder.design_job import DesignJob

from .context import L3VPNContext


class L3vpnDesign(DesignJob):
    """Create a l3vpn connection."""

    customer_name = StringVar()

    pe = ObjectVar(
        label="PE device",
        description="PE device for l3vpn",
        model=Device,
    )

    ce = ObjectVar(
        label="CE device",
        description="CE device for l3vpn",
        model=Device,
    )

    class Meta:
        """Metadata needed to implement the l3vpn design."""

        name = "L3VPN Design"
        commit_default = False
        design_file = "designs/0001_design.yaml.j2"
        context_class = L3VPNContext

    @staticmethod
    def validate_data_logic(data):
        """Validate the L3VPN Design data."""
        if data["ce"] == data["pe"]:
            raise ValidationError("Both routers can't be the same.")
