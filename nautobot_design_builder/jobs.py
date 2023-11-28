"""Generic Design Builder Jobs."""
from django.conf import settings
from django.db import transaction
from nautobot.dcim.models import Device, Site
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.jobs import IntegerVar, Job, JobHookReceiver, JobButtonReceiver, MultiObjectVar
from .models import DesignInstance, Journal
from nautobot.core.graphql import execute_query
from django.contrib.contenttypes.models import ContentType
from .choices import DesignInstanceStatusChoices
from nautobot.extras.models import Status
import time


# DesignDecommission Job
# Args:
#   - designinstance names (many)
#
# Logic:
#   - pre-hook to allow custom validation
#   - Go over journals to delete JournalEntries either Object, Attribute, or AttributeFields
#       - Take into account the proper order for deletion, could I trust the order of the Journal?
#   - How to enforce that there are not dependencies issues?
#       - Go over "active" Journals to see dependencies?
#            - Start from Jounral and check before deleting
#       - Use the CustomValidator of Nautobot objects to make sure that its not referenced by a Journal (active)
#             - make it for all objects, and the validation happens at then
#           - This takes into account the outside of Design Builder someone changes things


# QUESTIONS
#   - Why a DesignInstance can have many different Journals?
#       - Not well defined, but maybe for supporing updates?
#       - TO COVER AN UPDATE
#   - Why are we using the enforce_managed_fields in our Design and DesignInstance instead of using proper Django constructs?
#       - it's redundant when using editable
#       - I WAS WRONG ABOUT MY IDEA, it's not a full enforcement
#   - enforce_managed_fields (it's a different approach) should take into account the Journal references rather than being absolute
#       - A Device may have been created by a Design or manually, the second should not be taken into account for dependencies
#       - we should take into account the journal
#       - Custom validator for all object, similar approach for data validation
#       - Maybe SSOT jobs would skip the validate_save?
#   - Should we add a TAG in all the created/updated objects?
#       - Helpful for operator
#   - In the journal entry, even for newly created objects, we need to define which fields have been defined to not overwrite them
#       - If a journal contains a reference to a design_object, I can only change fields not "referenced"
#       - The journal entry should protect against trying to remove the object from another place
#   - If a Design Instance has to CREATE objects, it can be run twice. It should detect that the objects to be created are there
#       - WE SHOULD FAIL IF DATA CONFLICTS

# FEEDBACK
#
#   - Update works to demo multiple journals


class DesignInstanceDecommissioning(Job):
    design_instances = MultiObjectVar(
        model=DesignInstance,
        query_params={"status": "active"},
        description="Design Instances to decommission.",
    )

    class Meta:
        name = "Decommission Design Instances."
        description = """Job to decommission one or many Design Instances from Nautobot."""

    def proceed_after_pre_decommission_hook(self, design_instance):
        self.log_info(
            f"Checking if the design instance {design_instance} can be decommissioned by external dependencies."
        )
        time.sleep(5)
        self.log_success(f"No dependency issues found for {design_instance}.")
        return True

    def run(self, data, commit):
        design_instances = data["design_instances"]
        self.log_info(
            message=f"Starting decommissioning of design instances: {', '.join([instance.name for instance in design_instances])}",
        )

        for design_instance in design_instances:
            if not self.proceed_after_pre_decommission_hook(design_instance):
                self.log_warning(design_instance, message="Dependency issues found to this Design Instance.")
                continue

            self.log_info(obj=design_instance, message="Working on resetting objects for this Design Instance...")
            # TODO: we have to cover all the journals
            latest_journal = design_instance.journal_set.order_by("created").last()
            self.log_info(latest_journal, "Journal to be decommissioned.")

            for journal_entry in reversed(latest_journal.entries.all().order_by("last_updated")):
                if journal_entry.design_object:
                    object_description = str(journal_entry.design_object)
                    self.log_debug(f"Decommissioning changes for {object_description}...")

                    if journal_entry.full_control:
                        # TODO: find a better way to validate that the design_object is not referenced by others
                        for j in Journal.objects.all():
                            if j.design_instance.status.name == DesignInstanceStatusChoices.DECOMMISSIONED:
                                continue
                            if j == latest_journal:
                                continue
                            for j_entry in j.entries.all():
                                if journal_entry.design_object == j_entry.design_object:
                                    self.log_failure(
                                        journal_entry.design_object,
                                        message=f"This object is referenced by other active Journals: {j}",
                                    )
                                    # TODO: Maybe better to rollback after all analysis is done.
                                    raise ValueError(
                                        "Because of cross-references between design instances, decommission has been rollbacked."
                                    )

                        journal_entry.design_object.delete()
                        self.log_success(
                            obj=journal_entry.design_object, message=f"Object {object_description} removed."
                        )
                    else:
                        # TODO: make Nikos happy
                        # We have to me it more sophisticated
                        for attribute in journal_entry.changes["differences"].get("added", {}):
                            value_added = journal_entry.changes["differences"]["added"][attribute]
                            old_value = journal_entry.changes["differences"]["removed"][attribute]
                            if isinstance(old_value, dict):
                                # TODO: I'm assuming that the dict value only contains the keys added
                                current_value = getattr(journal_entry.design_object, attribute)
                                for key, _ in current_value:
                                    if key in value_added:
                                        current_value = old_value[key]
                                setattr(journal_entry.design_object, attribute, current_value)
                            else:
                                setattr(journal_entry.design_object, attribute, old_value)

                            journal_entry.design_object.save()
                        self.log_success(
                            obj=journal_entry.design_object,
                            message="Because not full control, we have restored ot ot the previous state.",
                        )

            content_type = ContentType.objects.get_for_model(DesignInstance)
            design_instance.status = Status.objects.get(
                content_types=content_type, name=DesignInstanceStatusChoices.DECOMMISSIONED
            )

            design_instance.save()

            self.log_success(f"{design_instance} has been successfully decommissioned from Nautobot.")


jobs = (DesignInstanceDecommissioning,)
