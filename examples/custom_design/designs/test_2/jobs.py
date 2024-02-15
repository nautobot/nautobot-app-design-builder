"""Test 2."""

from nautobot_design_builder.design_job import DesignJob
from nautobot.dcim.models import Device, Site, Location, Interface
from nautobot.extras.jobs import ObjectVar
from nautobot_design_builder.contrib import ext

from .context import WANtestContext


class wantest(DesignJob):
    """Class wantest."""

    ce_device = ObjectVar(
        label="ce Device",
        description="Select the ce Device",
        model=Device,
    )

    ce_interface = ObjectVar(
        label="ce Interface",
        description="Select the ce Interface",
        model=Interface,
        query_params={"device_id": "$ce_device"},
    )

    ces_device = ObjectVar(
        label="ces Device",
        description="Select the ces Device",
        model=Device,
    )

    ces_site = ObjectVar(
        label="ces Site",
        description="Select the ces Site",
        model=Site,
    )

    ces_location = ObjectVar(
        label="ces Location",
        description="Select the ces Location",
        model=Location,
    )

    co_device = ObjectVar(
        label="co Device",
        description="Select the co Device",
        model=Device,
    )

    co_site = ObjectVar(
        label="co Site",
        description="Select the co Site",
        model=Site,
    )

    co_location = ObjectVar(
        label="co Location",
        description="Select the co Location",
        model=Location,
    )

    cer_device = ObjectVar(
        label="Remote ce Device",
        description="Select the remote ce Device",
        model=Device,
    )

    cer_site = ObjectVar(
        label="Remote ce Site",
        description="Select the cer Site",
        model=Site,
    )

    cer_location = ObjectVar(
        label="Remote ce Location",
        description="Select the cer Location",
        model=Location,
    )

    class Meta:
        """Meta."""

        name = "WAN Test Design"
        commit_default = False
        design_file = "designs/wan_test_design.yaml.j2"
        context_class = WANtestContext
        extensions = [ext.CableConnectionExtension]
