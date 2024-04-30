"""Design to create a l3vpn site."""

from django.core.exceptions import ValidationError

from nautobot.dcim.models import Device, Interface
from nautobot.extras.jobs import ObjectVar, StringVar

from nautobot_design_builder.design_job import DesignJob
from nautobot_design_builder.design import ModelInstance
from nautobot_design_builder.ext import AttributeExtension
from nautobot_design_builder.contrib import ext

from .context import L3VPNContext


class NextInterfaceExtension(AttributeExtension):
    """Attribute extension to calculate the next available interface name."""

    tag = "next_interface"

    def attribute(self, *args, value, model_instance: ModelInstance) -> dict:
        """Determine the next available interface name.

        Args:
            *args: Any additional arguments following the tag name. These are `:` delimited.
            value (Any): The value of the data structure at this key's point in the design YAML. This could be a scalar, a dict or a list.
            model_instance (ModelInstance): Object is the ModelInstance that would ultimately contain the values.

        Returns:
            dict: Dictionary with the new interface name `{"!create_or_update:name": new_interface_name}
        """
        root_interface_name = "GigabitEthernet"
        previous_interfaces = self.environment.design_instance.get_design_objects(Interface).values_list(
            "id", flat=True
        )
        interfaces = model_instance.relationship_manager.filter(
            name__startswith="GigabitEthernet",
        )
        existing_interface = interfaces.filter(
            pk__in=previous_interfaces,
            tags__name="VRF Interface",
        ).first()
        if existing_interface:
            model_instance.instance = existing_interface
            return {"!create_or_update:name": existing_interface.name}
        return {"!create_or_update:name": f"{root_interface_name}1/{len(interfaces) + 1}"}


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
        design_files = [
            "designs/0001_ipam.yaml.j2",
            "designs/0002_devices.yaml.j2",
        ]
        context_class = L3VPNContext
        extensions = [
            ext.CableConnectionExtension,
            ext.NextPrefixExtension,
            NextInterfaceExtension,
            ext.ChildPrefixExtension,
        ]

    @staticmethod
    def validate_data_logic(data):
        """Validate the L3VPN Design data."""
        if data["ce"] == data["pe"]:
            raise ValidationError("Both routers can't be the same.")
