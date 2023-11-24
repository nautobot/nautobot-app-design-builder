"""Generic Design Builder Jobs."""
from django.conf import settings
from django.db import transaction
from nautobot.dcim.models import Device, Site
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.jobs import IntegerVar, Job, JobHookReceiver, JobButtonReceiver, MultiObjectVar
from .models import DesignInstance
from nautobot.core.graphql import execute_query
from django.contrib.contenttypes.models import ContentType
from .choices import DesignInstanceStatusChoices
from nautobot.extras.models import Status


# TODO: DesignDecommission Job
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
#       - Not well defined
#   - Why are we using the enforce_managed_fields in our Design and DesignInstance instead of using proper Django constructs?
#       - IT'S REDUNDANT TODAY with EDITABLE
#   - enforce_managed_fields should take into account the Journal references rather than being absolute
#       - A Device may have been created by a Design or manually, the second should not be taken into account for dependencies
#       - WE SHOULD TAKE INTO ACCOUNT THE JOURNAL


class DesignInstanceDecommissioning(Job):
    design_instances = MultiObjectVar(
        model=DesignInstance, query_params={"status": "active"}, description="Design Instances to decommission."
    )

    class Meta:
        name = "Design Instance Decommissioning"
        description = """Job to decommission Design Instances."""

    def run(self, data, commit):
        design_instances = data["design_instances"]

        for design_instance in design_instances:
            self.log_info(obj=design_instance, message="Decommissioning the objects for this Desing Instance.")
            latest_journal = design_instance.journal_set.order_by("created").last()
            self.log_info(latest_journal)
            for journal_entry in reversed(latest_journal.entries.all()):
                self.log_info(obj=journal_entry.design_object, message="Removing object.")
                if journal_entry.full_control is True:
                    journal_entry.design_object.delete()
                else:
                    self.log_info(message="Because not full control, we have to clean only attributes.")

            content_type = ContentType.objects.get_for_model(DesignInstance)
            design_instance.status = Status.objects.get(
                content_types=content_type, name=DesignInstanceStatusChoices.DECOMMISSIONED
            )

            design_instance.save()


jobs = (DesignInstanceDecommissioning,)
