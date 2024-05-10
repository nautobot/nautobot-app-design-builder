"""Generic Design Builder Jobs."""

from nautobot.extras.jobs import Job, MultiObjectVar

from .logging import get_logger
from .models import DesignInstance


name = "Design Builder"  # pylint: disable=invalid-name


class DesignInstanceDecommissioning(Job):
    """Job to decommission Design Instances."""

    design_instances = MultiObjectVar(
        model=DesignInstance,
        query_params={"status": "active"},
        description="Design Deployments to decommission.",
    )

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta class."""

        name = "Decommission Design Deployments"
        description = """Job to decommission one or many Design Deployments from Nautobot."""

    def run(self, data, commit):
        """Execute Decommissioning job."""
        design_instances = data["design_instances"]
        self.log_info(
            message=f"Starting decommissioning of design instances: {', '.join([instance.name for instance in design_instances])}",
        )

        for design_instance in design_instances:
            self.log_info(obj=design_instance, message="Working on resetting objects for this Design Deployment...")
            design_instance.decommission(local_logger=get_logger(__name__, self.job_result))
            self.log_success(f"{design_instance} has been successfully decommissioned from Nautobot.")


jobs = (DesignInstanceDecommissioning,)
