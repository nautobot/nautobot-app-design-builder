"""Generic Design Builder Jobs."""
from django.contrib.contenttypes.models import ContentType

from nautobot.extras.models import Status
from nautobot.extras.jobs import Job, MultiObjectVar

from . import DesignBuilderConfig
from .logging import get_logger
from .models import DesignInstance
from .choices import DesignInstanceStatusChoices


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

    # TODO: check if we could use Django Signals for hooks
    def _check_hook(self, design_instance, hook_type):
        """If configured, run a pre/post hook.

        It should return True if it's good to go, or False and the reason of the failure.
        """
        if hook_type == "pre":
            func = DesignBuilderConfig.pre_decommission_hook
        elif hook_type == "post":
            func = DesignBuilderConfig.post_decommission_hook
        else:
            raise ValueError(f"{hook_type} is not a valid hook type: pre or post")

        if not func:
            self.log_debug(f"No function found for {hook_type}-decommission hook.")
            return

        self.log_info(
            f"{hook_type}-validation checking if the design instance {design_instance} can be decommissioned by external dependencies."
        )

        result, reason = func(design_instance)

        if not result:
            self.log_failure(design_instance, message=f"The {hook_type} hook validation failed due to: {reason}")
            raise ValueError(f"{hook_type}-decommission hook validation failed.")

        self.log_success(f"No dependency issues found for {design_instance}.")

    def run(self, data, commit):
        """Execute Decommissioning job."""
        design_instances = data["design_instances"]
        self.log_info(
            message=f"Starting decommissioning of design instances: {', '.join([instance.name for instance in design_instances])}",
        )

        for design_instance in design_instances:
            found_cross_references = False
            self._check_hook(design_instance, "pre")

            self.log_info(obj=design_instance, message="Working on resetting objects for this Design Instance...")

            # TODO: When update mode is available, this should cover the journals stacked
            # Also, I feel like decommissioning a design instance can be extracted into
            # the `DesignInstance` class, much like we've done for `Journal.revert` and 
            # `JournalEntry.revert`. I think this would also make it easier to unit test
            # the functionality.
            latest_journal = design_instance.journal_set.order_by("created").last()
            self.log_info(latest_journal, "Journal to be decommissioned.")

            latest_journal.revert(local_logger=get_logger(__name__, self.job_result))
            content_type = ContentType.objects.get_for_model(DesignInstance)
            design_instance.status = Status.objects.get(
                content_types=content_type, name=DesignInstanceStatusChoices.DECOMMISSIONED
            )
            design_instance.save()
            # TODO: At the moment this is always `False` so we need to figure
            # out what the original intent was. I believe that this is handled
            # now with exceptions from the two `revert` methods.
            if found_cross_references:
                raise ValueError(
                    "Because of cross-references between design instances, decommissioning has been cancelled."
                )

            self._check_hook(design_instance, "post")

            self.log_success(f"{design_instance} has been successfully decommissioned from Nautobot.")


jobs = (DesignInstanceDecommissioning,)
