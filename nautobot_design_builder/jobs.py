"""Generic Design Builder Jobs."""
from nautobot.extras.jobs import Job, MultiObjectVar

from .logging import get_logger
from .models import DesignInstance


class DesignInstanceDecommissioning(Job):
    """Job to decommission Design Instances."""

    design_instances = MultiObjectVar(
        model=DesignInstance,
        query_params={"status": "active"},
        description="Design Instances to decommission.",
    )

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta class."""

        name = "Decommission Design Instances."
        description = """Job to decommission one or many Design Instances from Nautobot."""

    def run(self, data, commit):
        """Execute Decommissioning job."""
        design_instances = data["design_instances"]
        self.log_info(
            message=f"Starting decommissioning of design instances: {', '.join([instance.name for instance in design_instances])}",
        )

        for design_instance in design_instances:
            found_cross_references = False

            self.log_info(obj=design_instance, message="Working on resetting objects for this Design Instance...")

            # TODO: When update mode is available, this should cover the journals stacked
            design_instance.decommission(local_logger=get_logger(__name__, self.job_result))

            # TODO: At the moment this is always `False` so we need to figure
            # out what the original intent was. I believe that this is handled
            # now with exceptions from the two `revert` methods.
            if found_cross_references:
                raise ValueError(
                    "Because of cross-references between design instances, decommissioning has been cancelled."
                )

            self.log_success(f"{design_instance} has been successfully decommissioned from Nautobot.")


jobs = (DesignInstanceDecommissioning,)
