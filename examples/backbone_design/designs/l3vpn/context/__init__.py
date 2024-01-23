from django.core.exceptions import ObjectDoesNotExist
import ipaddress
from functools import lru_cache

from nautobot.dcim.models import Device, Interface
from nautobot.ipam.models import VRF, Prefix

from nautobot_design_builder.context import Context, context_file
from nautobot_design_builder.util import nautobot_version


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
        existing_prefix = Prefix.objects.filter(description=self.get_instance_name("useless arg")).first()
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

    def get_instance_name(self, useless_arg):
        if nautobot_version < "2.0.0":
            return self.job_result.job_kwargs["data"]["instance_name"]
        else:
            return self.job_result.job_kwargs["instance_name"]

    def get_interface_name(self, device):
        root_interface_name = "GigabitEthernet"
        interfaces = Interface.objects.filter(name__contains=root_interface_name, device=device)
        existing_interface = interfaces.filter(description=self.get_instance_name("useless arg")).first()
        if existing_interface:
            return existing_interface.name
        return f"{root_interface_name}1/{len(interfaces) + 1}"

    def get_ip_address(self, prefix, offset):
        net_prefix = ipaddress.ip_network(prefix)
        for count, host in enumerate(net_prefix):
            if count == offset:
                return f"{host}/{net_prefix.prefixlen}"
