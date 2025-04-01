"""Signal handlers that fire on various Django model signals."""

import logging
from itertools import chain

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver
from nautobot.apps import nautobot_database_ready
from nautobot.apps.choices import ColorChoices
from nautobot.extras.models import Job, Status

from . import choices
from .design_job import DesignJob
from .models import Deployment, Design

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
def create_deployment_statuses(**kwargs):
    """Create a default set of statuses for design deployments."""
    content_type = ContentType.objects.get_for_model(Deployment)
    color_mapping = {
        "Active": ColorChoices.COLOR_GREEN,
        "Decommissioned": ColorChoices.COLOR_GREY,
        "Disabled": ColorChoices.COLOR_GREY,
        "Unknown": ColorChoices.COLOR_DARK_RED,
    }
    for _, status_name in chain(choices.DeploymentStatusChoices):
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
        **kwargs: Additional keyword args from the signal.
    """
    job_class = instance.job_class
    if job_class and issubclass(job_class, DesignJob):
        _, created = Design.objects.get_or_create(job=instance)
        if created:
            _LOGGER.debug("Created design from %s", instance)
