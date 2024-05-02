"""Generic Design Builder Jobs."""

from nautobot.apps.jobs import Job, MultiObjectVar, register_jobs

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
        self.logger.info(
            "Starting decommissioning of design instances: %s", ", ".join([instance.name for instance in design_instances]),
        )

        for design_instance in design_instances:
            self.logger.info("Working on resetting objects for this Design Instance...", {"extra": {"object": design_instance}})
            design_instance.decommission(local_logger=get_logger(__name__, self.job_result))
            self.logger.info("%s has been successfully decommissioned from Nautobot.", design_instance)


register_jobs(DesignInstanceDecommissioning)
