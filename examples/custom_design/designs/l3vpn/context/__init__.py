from django.core.exceptions import ObjectDoesNotExist
import ipaddress

from nautobot.dcim.models import Device
from nautobot.ipam.models import VRF

from nautobot_design_builder.context import Context, context_file


@context_file("context.yaml")
class L3VPNContext(Context):
    """Render context for l3vpn design"""

    pe: Device
    ce: Device
    customer_name: str

    def __hash__(self):
        return hash((self.pe.name, self.ce.name, self.customer_name))

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

    def get_ip_address(self, prefix, offset):
        net_prefix = ipaddress.ip_network(prefix)
        for count, host in enumerate(net_prefix):
            if count == offset:
                return f"{host}/{net_prefix.prefixlen}"
