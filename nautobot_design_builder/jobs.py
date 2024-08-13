"""Generic Design Builder Jobs."""

from nautobot.apps.jobs import Job, MultiObjectVar, register_jobs

from .models import Deployment


name = "Design Builder"  # pylint: disable=invalid-name


class DeploymentDecommissioning(Job):
    """Job to decommission Deployments."""

    deployments = MultiObjectVar(
        model=Deployment,
        query_params={"status": "active"},
        description="Design Deployments to decommission.",
    )

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta class."""

        name = "Decommission Design Deployments"
        description = """Job to decommission one or many Design Deployments from Nautobot."""

    def run(self, deployments):  # pylint:disable=arguments-differ
        """Execute Decommissioning job."""
        self.logger.info(
            "Starting decommissioning of design deployments: %s",
            ", ".join([instance.name for instance in deployments]),
        )

        for deployment in deployments:
            self.logger.info("Working on resetting objects for this Design Instance...", extra={"object": deployment})
            deployment.decommission(local_logger=self.logger)
            self.logger.info("%s has been successfully decommissioned from Nautobot.", deployment)


register_jobs(DeploymentDecommissioning)
