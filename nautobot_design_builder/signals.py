from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver

from nautobot.core.signals import nautobot_database_ready
from nautobot.extras.models import Job, Status

from .design_job import DesignJob
from .models import Design
from . import choices

import logging

_LOGGER = logging.getLogger(__name__)


@receiver(nautobot_database_ready, sender=apps.get_app_config("nautobot_design_builder"))
def create_design_statuses(**kwargs):
    content_type = ContentType.objects.get_for_model(Design)
    for _, status_name in choices.DesignStatusChoices:
        status, _ = Status.objects.get_or_create(
            name=status_name,
        )
        status.content_types.add(content_type)


@receiver(post_save, sender=Job)
def create_design_model(sender, instance: Job, **kwargs):
    content_type = ContentType.objects.get_for_model(Design)
    status = Status.objects.get(content_types=content_type, name=choices.DesignStatusChoices.PENDING)
    if instance.job_class and issubclass(instance.job_class, DesignJob):
        _, created = Design.objects.get_or_create(
            job=instance,
            defaults={
                "status": status,
            },
        )
        if created:
            _LOGGER.debug("Created design from %s", instance)
