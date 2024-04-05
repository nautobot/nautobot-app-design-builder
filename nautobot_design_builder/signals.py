"""Signal handlers that fire on various Django model signals."""

from itertools import chain
import logging

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.db.models.signals import pre_delete
from django.db.models import ProtectedError

from nautobot.core.signals import nautobot_database_ready
from nautobot.extras.models import Job, Status
from nautobot.utilities.choices import ColorChoices
from nautobot.extras.registry import registry
from nautobot_design_builder.models import JournalEntry
from nautobot_design_builder.middleware import GlobalRequestMiddleware

from .design_job import DesignJob
from .models import Design, DesignInstance
from . import choices

_LOGGER = logging.getLogger(__name__)


@receiver(nautobot_database_ready, sender=apps.get_app_config("nautobot_design_builder"))
def create_design_model_for_existing(sender, **kwargs):
    """When the plugin is first installed, make sure each design job has a corresponding Design model.

    This is necessary if an older version of Design Builder was installed. In that case
    the design jobs exist, but not any design models. Since post-upgrade
    doesn't re-install those jobs, they aren't created in the database yet.
    """
    for job in Job.objects.all():
        create_design_model(sender, instance=job)


@receiver(nautobot_database_ready, sender=apps.get_app_config("nautobot_design_builder"))
def create_design_instance_statuses(**kwargs):
    """Create a default set of statuses for design instances."""
    content_type = ContentType.objects.get_for_model(DesignInstance)
    color_mapping = {
        "Active": ColorChoices.COLOR_GREEN,
        "Decommissioned": ColorChoices.COLOR_GREY,
        "Disabled": ColorChoices.COLOR_GREY,
        "Deployed": ColorChoices.COLOR_GREEN,
        "Pending": ColorChoices.COLOR_ORANGE,
        "Rolled back": ColorChoices.COLOR_RED,
    }
    for _, status_name in chain(choices.DesignInstanceStatusChoices, choices.DesignInstanceLiveStateChoices):
        status, _ = Status.objects.get_or_create(name=status_name, defaults={"color": color_mapping[status_name]})
        status.content_types.add(content_type)


@receiver(post_save, sender=Job)
def create_design_model(sender, instance: Job, **kwargs):  # pylint:disable=unused-argument
    """Create a `Design` instance for each `DesignJob`.

    This receiver will fire every time a `Job` instance is saved. If the
    `Job` inherits from `DesignJob` then look for a corresponding `Design`
    model in the database and create it if not found.

    Args:
        sender: The Job class
        instance (Job): Job instance that has been created or updated.
    """
    if instance.job_class and issubclass(instance.job_class, DesignJob):
        version = instance.job_class.Meta.version if hasattr(instance.job_class.Meta, "version") else "Not defined"
        _, created = Design.objects.get_or_create(job=instance, defaults={"version": version})
        if created:
            _LOGGER.debug("Created design from %s", instance)


def model_delete_design_builder(instance, **kwargs):
    """Delete."""
    request = GlobalRequestMiddleware.get_current_request()
    if (
        request
        and settings.PLUGINS_CONFIG["nautobot_design_builder"]["protected_superuser_bypass"]
        and request.user.is_superuser
    ):
        return

    for journal_entry in JournalEntry.objects.filter(
        _design_object_id=instance.id, active=True
    ).exclude_decommissioned():
        # If there is a design with full_control, only the design can delete it
        if (
            hasattr(instance, "_current_design")
            and instance._current_design == journal_entry.journal.design_instance  # pylint: disable=protected-access
            and journal_entry.full_control
        ):
            return
        raise ProtectedError("A design instance owns this object.", set([journal_entry.journal.design_instance]))


def load_pre_delete_signals():
    """Load pre delete handlers according to protected models."""
    for app_label, models in registry["model_features"]["custom_validators"].items():
        for model in models:
            if (app_label, model) in settings.PLUGINS_CONFIG["nautobot_design_builder"]["protected_models"]:
                model_class = apps.get_model(app_label=app_label, model_name=model)
                pre_delete.connect(model_delete_design_builder, sender=model_class)


load_pre_delete_signals()
