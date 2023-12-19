"""Generic Design Builder Jobs."""
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from nautobot.extras.models import Status
from nautobot.extras.jobs import Job, MultiObjectVar

from nautobot_design_builder import DesignBuilderConfig
from nautobot_design_builder.models import DesignInstance
from nautobot_design_builder.choices import DesignInstanceStatusChoices


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
            latest_journal = design_instance.journal_set.order_by("created").last()
            self.log_info(latest_journal, "Journal to be decommissioned.")

            # TODO: we refactored the reversion of journal entries into the `JournalEntry` model.
            # We should do the same here and refactor this into the `Journal` model.
            for journal_entry in latest_journal.entries.exclude(_design_object_id=None).order_by("-last_updated"):
                self.log_debug(f"Decommissioning changes for {journal_entry.design_object}.")

                try:
                    # TODO: possibly return a value that indicates updated/deleted?
                    # it is really only helpful for the log message
                    journal_entry.revert()
                    self.log_success(
                        obj=journal_entry.design_object,
                        message="Restored the object to its previous state.",
                    )
                except ValidationError as ex:
                    self.log_failure(journal_entry.design_object, message=str(ex))
                    raise ValueError(ex)

            content_type = ContentType.objects.get_for_model(DesignInstance)
            design_instance.status = Status.objects.get(
                content_types=content_type, name=DesignInstanceStatusChoices.DECOMMISSIONED
            )
            design_instance.save()

            if found_cross_references:
                raise ValueError(
                    "Because of cross-references between design instances, decommissioning has been cancelled."
                )

            self._check_hook(design_instance, "post")

            self.log_success(f"{design_instance} has been successfully decommissioned from Nautobot.")


jobs = (DesignInstanceDecommissioning,)
