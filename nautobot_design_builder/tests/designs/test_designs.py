"""Design jobs used for unit testing."""

from nautobot.dcim.models import Manufacturer, Device, Interface
from nautobot.extras.jobs import StringVar, ObjectVar

from nautobot_design_builder.choices import DesignModeChoices
from nautobot_design_builder.design_job import DesignJob
from nautobot_design_builder.design import ModelInstance
from nautobot_design_builder.ext import Extension, AttributeExtension
from nautobot_design_builder.contrib import ext
from nautobot_design_builder.tests.designs.context import IntegrationTestContext


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


class NextInterfaceExtension(AttributeExtension):
    """Attribute extension to calculate the next available interface name."""

    tag = "next_interface"

    def attribute(self, *args, value, model_instance: ModelInstance) -> dict:
        """Determine the next available interface name.

        Args:
            *args: Any additional arguments following the tag name. These are `:` delimited.
            value (Any): The value of the data structure at this key's point in the design YAML. This could be a scalar, a dict or a list.
            model_instance (ModelInstance): Object is the ModelInstance that would ultimately contain the values.

        Returns:
            dict: Dictionary with the new interface name `{"!create_or_update:name": new_interface_name}
        """
        root_interface_name = "GigabitEthernet"
        previous_interfaces = self.environment.deployment.get_design_objects(Interface).values_list("id", flat=True)
        interfaces = model_instance.relationship_manager.filter(
            name__startswith="GigabitEthernet",
        )
        existing_interface = interfaces.filter(
            pk__in=previous_interfaces,
            tags__name="VRF Interface",
        ).first()
        if existing_interface:
            model_instance.instance = existing_interface
            return {"!create_or_update:name": existing_interface.name}
        return {"!create_or_update:name": f"{root_interface_name}1/{len(interfaces) + 1}"}


class IntegrationDesign(DesignJob):
    """Create a P2P connection."""

    customer_name = StringVar()

    device_a = ObjectVar(
        label="Device A",
        description="Device A for a P2P connection",
        model=Device,
    )

    device_b = ObjectVar(
        label="Device B",
        description="Device B for a P2P connection",
        model=Device,
    )

    class Meta:  # pylint:disable=too-few-public-methods
        """Metadata needed to implement the P2P design."""

        name = "P2P Connection Design"
        commit_default = False
        design_files = [
            "templates/integration_design_ipam.yaml.j2",
            "templates/integration_design_devices.yaml.j2",
        ]
        context_class = IntegrationTestContext
        extensions = [
            ext.CableConnectionExtension,
            ext.NextPrefixExtension,
            NextInterfaceExtension,
            ext.ChildPrefixExtension,
        ]
        design_mode = DesignModeChoices.DEPLOYMENT
