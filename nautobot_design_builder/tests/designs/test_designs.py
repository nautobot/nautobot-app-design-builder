"""Design jobs used for unit testing."""

from nautobot.dcim.models import Manufacturer, Device
from nautobot.extras.jobs import StringVar, ObjectVar

from nautobot_design_builder.design_job import DesignJob
from nautobot_design_builder.ext import Extension
from nautobot_design_builder.contrib import ext
from nautobot_design_builder.tests.designs.context import IntegrationTestContext
from nautobot_design_builder.util import nautobot_version


class SimpleDesign(DesignJob):
    """Simple design job."""

    instance = StringVar()
    manufacturer = ObjectVar(model=Manufacturer)

    class Meta:  # pylint: disable=too-few-public-methods
        name = "Simple Design"
        design_file = "templates/simple_design.yaml.j2"


class SimpleDesign3(DesignJob):
    """Simple design job with extra manufacturer."""

    class Meta:  # pylint: disable=too-few-public-methods
        name = "Simple Design 3"
        design_file = "templates/simple_design_3.yaml.j2"


class SimpleDesignReport(DesignJob):
    """Simple design job that includes a post-implementation report."""

    class Meta:  # pylint: disable=too-few-public-methods
        name = "Simple Design with Report"
        design_file = "templates/simple_design.yaml.j2"
        report = "templates/simple_report.md.j2"


class MultiDesignJob(DesignJob):
    """Design job that is implemented from multiple design files."""

    class Meta:  # pylint: disable=too-few-public-methods
        name = "Multi File Design"
        design_files = [
            "templates/simple_design.yaml.j2",
            "templates/simple_design_2.yaml.j2",
        ]


class MultiDesignJobWithError(DesignJob):
    """Design job that includes an error (for unit testing)."""

    class Meta:  # pylint: disable=too-few-public-methods
        name = "Multi File Design with Error"
        design_files = [
            "templates/simple_design.yaml.j2",
            "templates/simple_design.yaml.j2",
        ]


class CustomExtension(Extension):
    """Custom extension for testing."""

    attribute_tag = "custom_extension"


class DesignJobWithExtensions(DesignJob):
    """Design job that includes a custom extension."""

    class Meta:  # pylint: disable=too-few-public-methods
        name = "Design with Custom Extensions"
        design_file = "templates/simple_design.yaml.j2"
        extensions = [CustomExtension]


class DesignWithRefError(DesignJob):
    """Design job that raises a DesignImplementationError."""

    class Meta:  # pylint: disable=too-few-public-methods
        name = "Design with an invalid ref"
        design_file = "templates/design_with_ref_error.yaml.j2"


class DesignWithValidationError(DesignJob):
    """Design job that has objects with failing validation."""

    class Meta:  # pylint: disable=too-few-public-methods
        name = "Design with validation errors"
        design_file = "templates/design_with_validation_error.yaml.j2"


class IntegrationDesign(DesignJob):
    """Integration design job."""

    customer_name = StringVar()

    pe = ObjectVar(
        label="PE device",
        description="PE device for l3vpn",
        model=Device,
    )

    ce = ObjectVar(
        label="CE device",
        description="CE device for l3vpn",
        model=Device,
    )

    class Meta:  # pylint: disable=too-few-public-methods
        name = "Integration Design"
        context_class = IntegrationTestContext
        extensions = [ext.CableConnectionExtension]
        design_files = [
            "templates/integration_design_ipam.yaml.j2",
            "templates/integration_design_devices.yaml.j2",
        ]
