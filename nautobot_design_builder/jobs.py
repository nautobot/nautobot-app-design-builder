"""Generic Design Builder Jobs."""

from nautobot.extras.jobs import Job, MultiObjectVar

from .logging import get_logger
from .models import Deployment


name = "Design Builder"  # pylint: disable=invalid-name


class DeploymentDecommissioning(Job):
    """Job to decommission Design Instances."""

    deployments = MultiObjectVar(
        model=Deployment,
        query_params={"status": "active"},
        description="Design Deployments to decommission.",
    )

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta class."""

        name = "Decommission Design Deployments"
        description = """Job to decommission one or many Design Deployments from Nautobot."""

    def run(self, data, commit):
        """Execute Decommissioning job."""
        deployments = data["deployments"]
        self.log_info(
            message=f"Starting decommissioning of design instances: {', '.join([instance.name for instance in deployments])}",
        )

        for deployment in deployments:
            self.log_info(obj=deployment, message="Working on resetting objects for this Design Deployment...")
            deployment.decommission(local_logger=get_logger(__name__, self.job_result))
            self.log_success(f"{deployment} has been successfully decommissioned from Nautobot.")


jobs = (DeploymentDecommissioning,)
