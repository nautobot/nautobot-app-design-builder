"""Base DesignContext for testing."""

import ipaddress

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from nautobot.dcim.models import Device
from nautobot.ipam.models import VRF

from nautobot_design_builder.context import Context, context_file

# pylint: disable=missing-function-docstring, inconsistent-return-statements


@context_file("base_context_file")
class BaseContext(Context):
    """Empty context that loads the base_context_file."""


@context_file("context/integration_context.yaml")
class IntegrationTestContext(Context):
    """Render context for P2P design"""

    device_a: Device
    device_b: Device
    customer_name: str

    def __hash__(self):
        return hash((self.device_a.name, self.device_b.name, self.customer_name))

    def validate_unique_devices(self):
        if self.device_a == self.device_b:
            raise ValidationError({"device_a": "Both routers can't be the same."})

    def get_customer_id(self, customer_name, p2p_asn):
        try:
            vrf = VRF.objects.get(name=customer_name)
            return vrf.rd.replace(f"{p2p_asn}:", "")
        except ObjectDoesNotExist:
            last_vrf = VRF.objects.filter(rd__startswith=p2p_asn).last()
            if not last_vrf:
                return "1"
            new_id = int(last_vrf.rd.split(":")[-1]) + 1
            return str(new_id)

    def get_ip_address(self, prefix, offset):
        net_prefix = ipaddress.ip_network(prefix)
        for count, host in enumerate(net_prefix):
            if count == offset:
                return f"{host}/{net_prefix.prefixlen}"

    def vrf_prefix_tag_name(self):
        return f"{self.deployment_name} VRF Prefix"


@context_file("context/verify_design.yaml")
class VerifyDesignContext(Context):
    """Setup variables from context yaml and Python for testing"""

    additional_manufacturer_1: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.additional_manufacturer_2 = "Manufacturer From Context"
