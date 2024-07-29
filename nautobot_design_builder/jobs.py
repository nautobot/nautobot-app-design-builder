"""Generic Design Builder Jobs."""

from nautobot.extras.jobs import Job, MultiObjectVar, BooleanVar

from .logging import get_logger
from .models import Deployment


name = "Design Builder"  # pylint: disable=invalid-name


class DeploymentDecommissioning(Job):
    """Job to decommission Design Deployments."""

    deployments = MultiObjectVar(
        model=Deployment,
        query_params={"status": "active"},
        description="Design Deployments to decommission.",
    )
    delete = BooleanVar(
        description="Actually delete the objects, not just their link to the design delpoyment.",
        default=True,
    )

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta class."""

        name = "Decommission Design Deployments"
        description = """Job to decommission one or many Design Deployments from Nautobot."""

    def run(self, data, commit):
        """Execute Decommissioning job."""
        deployments = data["deployments"]
        delete = data["delete"]

        self.log_info(
            message=f"Starting decommissioning of design deployments: {', '.join([instance.name for instance in deployments])}",
        )

        for deployment in deployments:
            if delete:
                message = "Working on deleting objects for this Design Deployment."
            else:
                message = "Working on unlinking objects from this Design Deployment."
            self.log_info(obj=deployment, message=message)

            deployment.decommission(local_logger=get_logger(__name__, self.job_result), delete=delete)

            if delete:
                message = f"{deployment} has been successfully decommissioned from Nautobot."
            else:
                message = f"Objects have been successfully unlinked from {deployment}."

            self.log_success(message)


jobs = (DeploymentDecommissioning,)
