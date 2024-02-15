from nautobot.dcim.models import Region, Site

from netaddr import IPNetwork

from nautobot_design_builder.errors import DesignValidationError
from nautobot_design_builder.context import Context, context_file


@context_file("context.yaml")
class CoreSiteContext(Context):
    """Render context for core site design"""

    region: Region
    site_name: str
    site_prefix: IPNetwork

    def validate_new_site(self):
        try:
            Site.objects.get(name__iexact=str(self.site_name))
            raise DesignValidationError(f"Another site exist with the name {self.site_name}")
        except Site.DoesNotExist:
            return

    def get_serial_number(self, device_name):
        # ideally this would be an API call, or some external
        # process, to determine the serial number. This is just to
        # demonstrate var lookup from the context object
        return str(abs(hash(device_name)))
