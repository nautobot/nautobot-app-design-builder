"""Middleware to allow custom delete logic."""

from django.conf import settings
from django.db.models.signals import pre_delete
from django.apps import apps
from django.db.models import ProtectedError
from django.utils.deprecation import MiddlewareMixin
from nautobot.extras.registry import registry
from nautobot_design_builder.models import JournalEntry


def model_delete_design_builder(instance, **kwargs):
    """Delete."""
    if (
        settings.PLUGINS_CONFIG["nautobot_design_builder"]["protected_superuser_bypass"]
        and model_delete_design_builder.request.user.is_superuser
    ):
        return

    for journal_entry in JournalEntry.objects.filter(
        _design_object_id=instance.id, active=True
    ).exclude_decommissioned():
        # If there is a design with full_control, only the design can delete it
        if (
            hasattr(instance, "_current_design")
            and instance._current_design == journal_entry.journal.design_instance  # pylint: disable=protected-access
            and journal_entry.full_control == True
        ):
            return

        raise ProtectedError("A design instance owns this object.", [journal_entry.journal.design_instance])


class PreDeleteMiddleware(MiddlewareMixin):  # pylint: disable=too-few-public-methods
    """Mixin to add a custom delete logic for protected models."""

    def process_view(self, request, view_func, view_args, view_kwargs):  # pylint: disable=unused-argument
        """Add custom delete pre_delete signal for the protected models."""
        model_delete_design_builder.request = request
        for app_label, models in registry["model_features"]["custom_validators"].items():
            for model in models:
                if (app_label, model) in settings.PLUGINS_CONFIG["nautobot_design_builder"]["protected_models"]:
                    model_class = apps.get_model(app_label=app_label, model_name=model)
                    pre_delete.connect(model_delete_design_builder, sender=model_class)
