"""Base DesignContext for testing."""

import ipaddress
from django.core.exceptions import ObjectDoesNotExist


from nautobot.dcim.models import Device
from nautobot.ipam.models import VRF
from nautobot_design_builder.context import Context, context_file

# pylint: disable=missing-function-docstring, inconsistent-return-statements


@context_file("base_context_file")
class BaseContext(Context):
    """Empty context that loads the base_context_file."""


@context_file("context/integration_context.yaml")
class IntegrationTestContext(Context):
    """Render context for integration test design."""

    pe: Device
    ce: Device
    customer_name: str

    def __hash__(self):
        return hash((self.pe.name, self.ce.name, self.customer_name))

    def get_customer_id(self, customer_name, p2p_asn):
        try:
            vrf = VRF.objects.get(description=f"VRF for customer {customer_name}")
            return vrf.name.replace(f"{p2p_asn}:", "")
        except ObjectDoesNotExist:
            last_vrf = VRF.objects.filter(name__contains=p2p_asn).last()
            if not last_vrf:
                return "1"
            new_id = int(last_vrf.name.split(":")[-1]) + 1
            return str(new_id)

    def get_ip_address(self, prefix, offset):
        net_prefix = ipaddress.ip_network(prefix)
        for count, host in enumerate(net_prefix):
            if count == offset:
                return f"{host}/{net_prefix.prefixlen}"

    def vrf_prefix_tag_name(self):
        return f"{self.deployment_name} VRF Prefix"

    def vrf_prefix_tag_slug(self):
        return self.vrf_prefix_tag_name().lower().replace(" ", "_")
