"""Base DesignContext for testing."""

from django.core.exceptions import ObjectDoesNotExist
import ipaddress
from functools import lru_cache

from nautobot.dcim.models import Device, Interface
from nautobot.ipam.models import VRF, Prefix
from nautobot_design_builder.context import Context, context_file


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

    @lru_cache
    def get_l3vpn_prefix(self, parent_prefix, prefix_length):
        tag = self.design_instance_tag
        if tag:
            existing_prefix = Prefix.objects.filter(tags__in=[tag], prefix_length=30).first()
            if existing_prefix:
                return str(existing_prefix)

        for new_prefix in ipaddress.ip_network(parent_prefix).subnets(new_prefix=prefix_length):
            try:
                Prefix.objects.get(prefix=str(new_prefix))
            except ObjectDoesNotExist:
                return new_prefix

    def get_customer_id(self, customer_name, l3vpn_asn):
        try:
            vrf = VRF.objects.get(description=f"VRF for customer {customer_name}")
            return vrf.name.replace(f"{l3vpn_asn}:", "")
        except ObjectDoesNotExist:
            last_vrf = VRF.objects.filter(name__contains=l3vpn_asn).last()
            if not last_vrf:
                return "1"
            new_id = int(last_vrf.name.split(":")[-1]) + 1
            return str(new_id)

    def get_interface_name(self, device):
        root_interface_name = "GigabitEthernet"
        interfaces = Interface.objects.filter(name__contains=root_interface_name, device=device)
        tag = self.design_instance_tag
        if tag:
            existing_interface = interfaces.filter(tags__in=[tag]).first()
            if existing_interface:
                return existing_interface.name
        return f"{root_interface_name}1/{len(interfaces) + 1}"

    def get_ip_address(self, prefix, offset):
        net_prefix = ipaddress.ip_network(prefix)
        for count, host in enumerate(net_prefix):
            if count == offset:
                return f"{host}/{net_prefix.prefixlen}"
