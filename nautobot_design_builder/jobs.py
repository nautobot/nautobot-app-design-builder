"""Generic Design Builder Jobs."""

from nautobot.apps.jobs import BooleanVar, Job, MultiObjectVar, register_jobs

from .models import Deployment

name = "Design Builder"  # pylint: disable=invalid-name


class DeploymentDecommissioning(Job):
    """Job to decommission Deployments."""

    deployments = MultiObjectVar(
        model=Deployment,
        query_params={"status": "active"},
        description="Design Deployments to decommission.",
    )

    delete = BooleanVar(
        description="Actually delete the objects, not just their link to the design deployment.",
        default=True,
    )

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta class."""

        name = "Decommission Design Deployments"
        description = """Job to decommission one or many Design Deployments from Nautobot."""

    def run(self, deployments, delete):  # pylint:disable=arguments-differ
        """Execute Decommissioning job."""
        self.logger.info(
            "Starting decommissioning of design deployments: %s",
            ", ".join([instance.name for instance in deployments]),
        )

        for deployment in deployments:
            if delete:
                message = "Deleting objects for this Design Deployment."
            else:
                message = "Unlinking objects from this Design Deployment."
            self.logger.info(message, extra={"object": deployment})

            deployment.decommission(local_logger=self.logger, delete=delete)

            if delete:
                self.logger.info("%s has been successfully decommissioned from Nautobot.", deployment)
            else:
                self.logger.info("Objects have been successfully unlinked from %s", deployment)


register_jobs(DeploymentDecommissioning)
