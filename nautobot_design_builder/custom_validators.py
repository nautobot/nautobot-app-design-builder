"""Design Builder custom validators to protect refernced objects."""

from django.conf import settings
from nautobot.extras.registry import registry
from nautobot.extras.plugins import PluginCustomValidator
from nautobot_design_builder.models import ChangeRecord
from nautobot_design_builder.middleware import GlobalRequestMiddleware


class BaseValidator(PluginCustomValidator):
    """Base PluginCustomValidator class that implements the core logic for enforcing validation rules defined in this app."""

    model = None

    def clean(self):
        """The clean method executes the actual rule enforcement logic for each model."""
        request = GlobalRequestMiddleware.get_current_request()
        if (
            request
            and settings.PLUGINS_CONFIG["nautobot_design_builder"]["protected_superuser_bypass"]
            and request.user.is_superuser
        ):
            return
        obj = self.context["object"]
        obj_class = obj.__class__

        # If it's a create operation there is nothing to protect against
        if not obj.present_in_database:
            return

        existing_object = obj_class.objects.get(id=obj.id)
        for record in ChangeRecord.objects.filter(  # pylint: disable=too-many-nested-blocks
            _design_object_id=obj.id, active=True
        ).exclude_decommissioned():

            for attribute in obj._meta.fields:
                attribute_name = attribute.name

                # Excluding private attributes
                if attribute_name.startswith("_"):
                    continue

                new_attribute_value = getattr(obj, attribute_name)
                current_attribute_value = getattr(existing_object, attribute_name)

                if new_attribute_value != current_attribute_value and (
                    attribute_name in record.changes["differences"].get("added", {})
                    and record.changes["differences"]["added"][attribute_name]
                ):
                    error_context = ""
                    # For dict attributes (i.e., JSON fields), the design builder can own only a few keys
                    if isinstance(current_attribute_value, dict):
                        for key, value in record.changes["differences"]["added"][attribute_name].items():
                            if new_attribute_value[key] != value:
                                error_context = f"Key {key}"
                                break
                        else:
                            # If all the referenced attributes are not changing, we can update it
                            return

                    # If the update is coming from the design instance owner, it can be updated
                    if (
                        hasattr(obj, "_current_design")
                        and obj._current_design  # pylint: disable=protected-access
                        == record.change_set.deployment
                    ):
                        continue

                    self.validation_error(
                        {
                            attribute_name: f"The attribute is managed by the Design Instance: {record.change_set.deployment}. {error_context}"
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
