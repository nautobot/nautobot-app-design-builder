"""Design to create a P2P connection."""

from nautobot.dcim.models import Device, Interface
from nautobot.extras.jobs import ObjectVar, StringVar

from nautobot_design_builder.choices import DesignModeChoices
from nautobot_design_builder.design_job import DesignJob
from nautobot_design_builder.design import ModelInstance
from nautobot_design_builder.ext import AttributeExtension
from nautobot_design_builder.contrib import ext

from .context import P2PContext


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
        previous_interfaces = self.environment.deployment.get_design_objects(Interface).values_list("id", flat=True)
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


class P2PDesign(DesignJob):
    """Create a p2p connection."""

    customer_name = StringVar()

    device_a = ObjectVar(
        label="Device A",
        description="Device A for P2P connection",
        model=Device,
    )

    device_b = ObjectVar(
        label="Device B",
        description="Device B for P2P connection",
        model=Device,
    )

    class Meta:
        """Metadata needed to implement the P2P design."""

        design_mode = DesignModeChoices.DEPLOYMENT
        name = "P2P Connection Design"
        commit_default = False
        design_files = [
            "designs/0001_ipam.yaml.j2",
            "designs/0002_devices.yaml.j2",
        ]
        context_class = P2PContext
        extensions = [
            ext.CableConnectionExtension,
            ext.NextPrefixExtension,
            NextInterfaceExtension,
            ext.ChildPrefixExtension,
        ]
        version = "0.5.1"
        description = "Connect via a direct cable two network devices using a P2P network."
        docs = """This design creates a P2P connection between two existing network devices.

The user input data is:
    - Customer name(string): is used to establish a per-client VRF that gets a /30 prefix allocated.
    - Device A (Device): one end of the P2P connection.
    - Device B (Device): the other end of the P2P connection.

The outcome of the design contains:
    - A /30 `Prefix` assigned to a customer `VRF`
    - A new `Interface` in each one of the Devices with a corresponding `IPAddress` from the previous `Prefix`
    - A cable connected to both `Interfaces`
"""
