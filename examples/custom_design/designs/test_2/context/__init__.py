from nautobot_design_builder.context import Context
from nautobot.dcim.models import Device, Site, Location, Interface
from nautobot.ipam.models import Prefix, Role
from nautobot_design_builder.util import nautobot_version


class WANtestContext(Context):
    """Render context for WAN test design."""

    ce_device: Device
    ce_interface: Interface
    ces_device: Device
    co_device: Device
    cer_device: Device
    ces_site: Site
    co_site: Site
    cer_site: Site
    ces_location: Location
    co_location: Location
    cer_location: Location

    def get_instance_name(self, useless_arg):
        if nautobot_version < "2.0.0":
            return self.job_result.job_kwargs["data"]["instance_name"]
        else:
            return self.job_result.job_kwargs["instance_name"]

    def get_next_available_prefix(self, rolename, prefix_length):
        existing_prefix = Prefix.objects.filter(
            description__in=f"Instance:{self.get_instance_name('useless arg')}"
        ).first()
        if existing_prefix:
            return str(existing_prefix)
        role = Role.objects.get(name=rolename)
        prefixes = Prefix.objects.filter(role=role)
        allocated_prefix = "none"
        try:
            for prefix in prefixes:
                if allocated_prefix != "none":
                    break

                available_prefixes = prefix.get_available_prefixes()
                # self.log_info(f"available_prefixes debug1: {available_prefixes}")
                for available_prefix in available_prefixes.iter_cidrs():
                    # self.log_info(f"available_prefixes debug2: {available_prefix.network} / {available_prefix.prefixlen}")
                    # allocated_prefix = f"{available_prefix.network}/{available_prefix.prefixlen}"
                    if prefix_length >= available_prefix.prefixlen:
                        allocated_prefix = f"{available_prefix.network}/{prefix_length}"
                        # self.log_info(f"debug3 new allocate: {allocated_prefix}")
                        # requested_prefix["prefix"] = allocated_prefix
                        # requested_prefix["vrf"] = prefix.vrf.pk if prefix.vrf else None
                        break

            # self.log_info(f"get_prefix, new allocate: {allocated_prefix}")
            return allocated_prefix

        except Exception:
            self.log_failure("get_prefix, no prefix available")
            raise  # exception thats stops except, give HTTP 4xx at "client"

    co_allocated_prefix = "10.255.0.0/32"
    cer_allocated_prefix = "10.255.0.1/32"

    def get_hostname(self, site, role):
        def hostname_check(hostname):
            try:
                Device.objects.get(name__iexact=str(hostname))
                return True
            except Device.DoesNotExist:
                return False

        inc = 1

        if role == "ces":
            hostname = f"ces-{site}-{inc:02d}"
            while hostname_check(hostname):
                inc += 1
                hostname = f"ces-{site}-{inc:02d}"

        elif role == "co":
            hostname = f"co-{site}-01"
            while hostname_check(hostname):
                inc += 1
                hostname = f"co-{site}-{inc:02d}"

        elif role == "cer":
            hostname = f"ce01-{site}"
            while hostname_check(hostname):
                inc += 1
                hostname = f"ce{inc:02d}-{site}"

        return hostname
