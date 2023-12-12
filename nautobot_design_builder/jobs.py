"""Generic Design Builder Jobs."""
from django.contrib.contenttypes.models import ContentType

from nautobot.extras.models import Status
from nautobot.extras.jobs import Job, MultiObjectVar

from .models import DesignInstance, JournalEntry
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

    def _proceed_after_pre_decommission_hook(self, design_instance):
        # TODO: how to make this more decoupled?
        self.log_info(
            f"Checking if the design instance {design_instance} can be decommissioned by external dependencies."
        )
        self.log_success(f"No dependency issues found for {design_instance}.")
        return True

    def _process_journal_entry_with_full_control(self, journal_entry):
        # With full control, we can delete the design_object is there are no active references
        # by other Journals
        other_journal_entries = (
            JournalEntry.objects.filter(_design_object_id=journal_entry.design_object.id)
            .exclude(id=journal_entry.id)
            .exclude(journal__design_instance__status__name=DesignInstanceStatusChoices.DECOMMISSIONED)
        )

        if other_journal_entries:
            self.log_failure(
                journal_entry.design_object,
                message=(
                    "This object is referenced by other active Journals: ",
                    f"{list(other_journal_entries.values_list('id', flat=True))}",
                ),
            )
            return False

        journal_entry.design_object.delete()

        self.log_success(obj=journal_entry.design_object, message=f"Object {journal_entry.design_object} removed.")

        return True

    def _process_journal_entry_without_full_control(self, journal_entry):
        # If we don't have full control, we recover the value of the items changed to the
        # previous value
        for attribute in journal_entry.changes["differences"].get("added", {}):
            value_changed = journal_entry.changes["differences"]["added"][attribute]
            old_value = journal_entry.changes["differences"]["removed"][attribute]
            if isinstance(value_changed, dict):
                # If the value is a dictionary (e.g., config context), we only update the
                # keys changed, honouring the current value of the attribute
                current_value = getattr(journal_entry.design_object, attribute)
                keys_to_remove = []
                for key in current_value:
                    if key in value_changed:
                        if old_value:
                            current_value = old_value[key]
                        else:
                            keys_to_remove.append(key)
                for key in keys_to_remove:
                    del current_value[key]
                setattr(journal_entry.design_object, attribute, current_value)
            else:
                setattr(journal_entry.design_object, attribute, old_value)

            journal_entry.design_object.save()

        self.log_success(
            obj=journal_entry.design_object,
            message="Because not full control, we have restored ot ot the previous state.",
        )

        return True

    def run(self, data, commit):
        """Execute job."""
        design_instances = data["design_instances"]
        self.log_info(
            message=f"Starting decommissioning of design instances: {', '.join([instance.name for instance in design_instances])}",
        )

        found_cross_references = False

        for design_instance in design_instances:
            if not self._proceed_after_pre_decommission_hook(design_instance):
                self.log_warning(design_instance, message="Dependency issues found to this Design Instance.")
                continue

            self.log_info(obj=design_instance, message="Working on resetting objects for this Design Instance...")

            # TODO: When update mode is available, this should cover the journals stacked
            latest_journal = design_instance.journal_set.order_by("created").last()
            self.log_info(latest_journal, "Journal to be decommissioned.")

            for journal_entry in reversed(
                latest_journal.entries.exclude(_design_object_id=None).order_by("last_updated")
            ):
                # if journal_entry.design_object:
                self.log_debug(f"Decommissioning changes for {journal_entry.design_object}.")

                if journal_entry.full_control:
                    if not self._process_journal_entry_with_full_control(journal_entry):
                        found_cross_references = True
                else:
                    self._process_journal_entry_without_full_control(journal_entry)

            content_type = ContentType.objects.get_for_model(DesignInstance)
            design_instance.status = Status.objects.get(
                content_types=content_type, name=DesignInstanceStatusChoices.DECOMMISSIONED
            )
            design_instance.save()

            if found_cross_references:
                raise ValueError(
                    "Because of cross-references between design instances, decommissioning has been cancelled."
                )

            self.log_success(f"{design_instance} has been successfully decommissioned from Nautobot.")


jobs = (DesignInstanceDecommissioning,)
