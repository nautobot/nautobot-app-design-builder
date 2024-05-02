"""Generic Design Builder Jobs."""

from nautobot.apps.jobs import register_jobs
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

    def run(self, **kwargs):
        """Execute Decommissioning job."""
        # TODO: implement dry run
        design_instances = kwargs["design_instances"]
        self.logger.info(
            f"Starting decommissioning of design instances: {', '.join([instance.name for instance in design_instances])}",
        )

        for design_instance in design_instances:
            # FIXME: this is not working
            # self.logger.info("Working on resetting objects for this Design Instance...", design_instance)
            self.logger.info("Working on resetting objects for this Design Instance...")
            design_instance.decommission(local_logger=get_logger(__name__, self.job_result))
            self.logger.info(f"{design_instance} has been successfully decommissioned from Nautobot.")


register_jobs(DesignInstanceDecommissioning)
