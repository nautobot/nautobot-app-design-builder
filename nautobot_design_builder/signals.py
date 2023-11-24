"""Signal handlers that fire on various Django model signals."""
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver

from nautobot.core.signals import nautobot_database_ready
from nautobot.extras.models import Job, Status

from .design_job import DesignJob
from .models import Design, DesignInstance
from . import choices
from nautobot.utilities.choices import ColorChoices

import logging

_LOGGER = logging.getLogger(__name__)


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
        "Rollbacked": ColorChoices.COLOR_RED,
    }
    for _, status_name in choices.DesignInstanceStatusChoices:
        status, _ = Status.objects.get_or_create(name=status_name, defaults={"color": color_mapping[status_name]})
        status.content_types.add(content_type)

    for _, status_name in choices.DesignInstanceOperStatusChoices:
        status, _ = Status.objects.get_or_create(name=status_name, defaults={"color": color_mapping[status_name]})
        status.content_types.add(content_type)


@receiver(post_save, sender=Job)
def create_design_model(sender, instance: Job, **kwargs):
    """Create a `Design` instance for each `DesignJob`.

    This receiver will fire every time a `Job` instance is saved. If the
    `Job` inherits from `DesignJob` then look for a corresponding `Design`
    model in the database and create it if not found.

    Args:
        sender: The Job class
        instance (Job): Job instance that has been created or updated.
    """
    content_type = ContentType.objects.get_for_model(Design)
    # status = Status.objects.get(content_types=content_type, name=choices.DesignStatusChoices.PENDING)
    if instance.job_class and issubclass(instance.job_class, DesignJob):
        _, created = Design.objects.get_or_create(
            job=instance,
            # defaults={
            #     "status": status,
            # },
        )
        if created:
            _LOGGER.debug("Created design from %s", instance)
