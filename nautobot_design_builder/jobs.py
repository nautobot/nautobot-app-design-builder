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
    only_traceability = BooleanVar(
        description="Only remove the objects traceability, not decommissioning the actual data.",
        default=False,
    )

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta class."""

        name = "Decommission Design Deployments"
        description = """Job to decommission one or many Design Deployments from Nautobot."""

    def run(self, data, commit):
        """Execute Decommissioning job."""
        deployments = data["deployments"]
        only_traceability = data["only_traceability"]

        self.log_info(
            message=f"Starting decommissioning of design deployments: {', '.join([instance.name for instance in deployments])}",
        )

        for deployment in deployments:
            if only_traceability:
                message = "Working on resetting traceability for this Design Deployment..."
            else:
                message = "Working on resetting objects for this Design Deployment..."
            self.log_info(obj=deployment, message=message)

            deployment.decommission(
                local_logger=get_logger(__name__, self.job_result), only_traceability=only_traceability
            )

            if only_traceability:
                message = f"Traceability for {deployment} has been successfully removed from Nautobot."
            else:
                message = f"{deployment} has been successfully decommissioned from Nautobot."

            self.log_success(message)


jobs = (DeploymentDecommissioning,)
