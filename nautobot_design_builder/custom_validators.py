"""Custom Validators definition."""
from nautobot.dcim.models import Region
from nautobot.extras.plugins import PluginCustomValidator
from nautobot.extras.models import CustomField
from nautobot_design_builder.models import Journal, DesignInstance
from nautobot_design_builder.choices import DesignInstanceStatusChoices


class RegionValidator(PluginCustomValidator):
    """Custom validator to validate that Device is not changed when referenced by a Journal."""

    model = "dcim.region"

    def clean(self):
        """Validate the journal."""

        try:
            existing_object = Region.objects.get(name=self.context["object"].name)
        except Region.DoesNotExist:
            pass
        for design_instance in DesignInstance.objects.all():
            if design_instance.status.name == DesignInstanceStatusChoices.DECOMMISSIONED:
                continue
            for journal in design_instance.journal_set.all():
                for journal_entry in journal.entries.all():
                    # TODO: make it general and using Django orm
                    if journal_entry.full_control:
                        continue
                    if not journal_entry:
                        continue
                    if journal_entry.design_object != existing_object:
                        continue
                    for attribute in journal_entry.changes["differences"].get("added", {}):
                        if getattr(self.context["object"], attribute) != getattr(existing_object, attribute):
                            self.validation_error(
                                {attribute: f"The attribute is managed by the Design Instance {design_instance.id}"}
                            )

        # if self.context['object'].tenant is None:
        #     # Enforce that all locations must have a tenant
        #     self.validation_error({
        #         "tenant": "All locations must have a tenant"
        #     })


custom_validators = [RegionValidator]
