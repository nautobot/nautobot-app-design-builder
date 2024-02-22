"""Design Builder custom validators to protect refernced objects."""

from django.conf import settings
from nautobot.extras.registry import registry
from nautobot.extras.plugins import PluginCustomValidator
from nautobot_design_builder.models import JournalEntry


class BaseValidator(PluginCustomValidator):
    """Base PluginCustomValidator class that implements the core logic for enforcing validation rules defined in this app."""

    model = None

    def clean(self):
        """The clean method executes the actual rule enforcement logic for each model."""
        if (
            settings.PLUGINS_CONFIG["nautobot_design_builder"]["protected_superuser_bypass"]
            and self.context["user"].is_superuser
        ):
            return

        obj = self.context["object"]
        obj_class = obj.__class__

        # If it's a create operation there is nothing to protect against
        if not obj.present_in_database:
            return

        existing_object = obj_class.objects.get(id=obj.id)

        # TODO: the update of region drops some info like the parent region!!!
        # TODO: how to protect local_context

        # TODO: how to manage updates of designs?, we should know if this comes from a design instance
        for journal_entry in JournalEntry.objects.filter(
            _design_object_id=obj.id, active=True
        ).exclude_decommissioned():

            for attribute in obj._meta.fields:
                attribute_name = attribute.name

                # Excluding private attributes
                if attribute_name.startswith("_"):
                    continue

                if getattr(obj, attribute_name) != getattr(existing_object, attribute_name):
                    if (
                        attribute_name in journal_entry.changes["differences"].get("added", {})
                        and journal_entry.changes["differences"]["added"][attribute_name]
                    ):
                        # If the update is coming from the design instance owner, it can be updated
                        if (
                            hasattr(obj, "_current_design")
                            and obj._current_design  # pylint: disable=protected-access
                            == journal_entry.journal.design_instance
                        ):
                            continue

                        self.validation_error(
                            {
                                attribute_name: f"The attribute is managed by the Design Instance {journal_entry.journal.id}"
                            }
                        )


class CustomValidatorIterator:  # pylint: disable=too-few-public-methods
    """Iterator that generates PluginCustomValidator classes for each model registered in the extras feature query registry 'custom_validators'."""

    def __iter__(self):
        """Return a generator of PluginCustomValidator classes for each registered model."""
        for app_label, models in registry["model_features"]["custom_validators"].items():
            for model in models:
                if (app_label, model) in settings.PLUGINS_CONFIG["nautobot_design_builder"]["protected_models"]:
                    yield type(
                        f"{app_label.capitalize()}{model.capitalize()}CustomValidator",
                        (BaseValidator,),
                        {"model": f"{app_label}.{model}"},
                    )


custom_validators = CustomValidatorIterator()
