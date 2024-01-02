from django.core.exceptions import ObjectDoesNotExist
import ipaddress
from functools import lru_cache

from nautobot.dcim.models import Device, Interface
from nautobot.ipam.models import VRF, Prefix

from nautobot_design_builder.context import Context, context_file


@context_file("context.yaml")
class L3VPNContext(Context):
    """Render context for l3vpn design"""

    pe: Device
    ce: Device
    customer_name: str

    def __hash__(self):
        return hash((self.pe.name, self.ce.name, self.customer_name))

    @lru_cache
    def get_l3vpn_prefix(self, parent_prefix, prefix_length):
        # get the next available prefix in l3vpn_prefix
        # parent_prefix = Prefix.objects.get(prefix=parent_prefix)
        # return parent_prefix.get_first_available_prefix()
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
            vrfs = VRF.objects.filter(name__contains=l3vpn_asn)
            return str(len(vrfs) + 1)

    def get_interface_name(self, device):
        root_interface_name = "GigabitEthernet"
        interfaces = Interface.objects.filter(name__contains=root_interface_name, device=device)
        return f"{root_interface_name}1/{len(interfaces) + 1}"

    def get_ip_address(self, prefix, offset):
        net_prefix = ipaddress.ip_network(prefix)
        for count, host in enumerate(net_prefix):
            if count == offset:
                return f"{host}/{net_prefix.prefixlen}"
