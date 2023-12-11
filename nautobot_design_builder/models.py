"""Collection of models that DesignBuilder uses to track design implementations."""
from typing import List
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import fields as ct_fields
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import models
from django.urls import reverse

from nautobot.apps.models import PrimaryModel
from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.extras.models import Job as JobModel, JobResult, StatusModel, StatusField
from nautobot.extras.utils import extras_features
from nautobot.utilities.querysets import RestrictedQuerySet

from nautobot_design_builder.util import nautobot_version
from nautobot_design_builder import choices


# TODO: this method needs to be put in the custom validators module.
# it will be used to enforce attributes managed by Design Builder
def enforce_managed_fields(
    new_model: models.Model, field_names: List[str], message="is managed by Design Builder and cannot be changed."
):
    """Raise a ValidationError if any field has changed that is non-editable.

    This method checks a model to determine if any managed fields have changed
    values. If there are changes to any of those fields then a ValidationError
    is raised.

    Args:
        new_model (models.Model): The model being saved.
        field_names (list[str]): A list of field names to check for changes.
        message (str, optional): The message to include in the
        validation error. Defaults to "is managed by Design Builder and cannot be changed.".

    Raises:
        ValidationError: the error will include all of the managed fields that have
        changed.
    """
    model_class = new_model.__class__

    old_model = model_class.objects.get(pk=new_model.pk)
    changed = {}
    for field_name in field_names:
        values = []
        for model in [old_model, new_model]:
            try:
                value = getattr(model, field_name)
                if isinstance(value, models.Model):
                    value = value.pk
            except ObjectDoesNotExist:
                value = None
            values.append(value)

        if values[0] != values[1]:
            field = getattr(model_class, field_name)
            display_name = field.field.verbose_name.title()
            changed[field_name] = f"{display_name} {message}"

    if changed:
        raise ValidationError(changed)


class DesignQuerySet(RestrictedQuerySet):
    """Queryset for `Design` objects."""

    def get_by_natural_key(self, name: str) -> "Design":
        """Retrieve a design by its job name.

        Args:
            name (str): The `name` of the job associated with the `Design`

        Returns:
            Design: The `Design` model instance associated with the job.
        """
        return self.get(job__name=name)

    def for_design_job(self, job: JobModel):
        """Get the related job for design."""
        return self.get(job=job)


class Design(PrimaryModel):
    """Design represents a single design job.

    Design may or may not have any instances (implementations), but
    is available for execution. It is largely a one-to-one type
    relationship with Job, but will only exist if the Job has a
    DesignJob in its ancestry.

    Instances of the Design model are created automatically from
    signals.

    In the future this model may include a version field to indicate
    changes to a design over time. It may also include a relationship
    to a saved graphql query at some point in the future.
    """

    # TODO: Add version field (future feature)
    # TODO: Add saved graphql query (future feature)
    job = models.ForeignKey(to=JobModel, on_delete=models.PROTECT, editable=False)

    objects = DesignQuerySet.as_manager()

    class Meta:
        """Meta class."""

        constraints = [
            models.UniqueConstraint(
                fields=["job"],
                name="unique_designs",
            ),
        ]

    def clean(self):
        """Guarantee that the design field cannot be changed."""
        super().clean()
        if not self._state.adding:
            enforce_managed_fields(self, ["job"], message="is a field that cannot be changed")

    @property
    def name(self):
        """Property for job name."""
        return self.job.name

    def get_absolute_url(self):
        """Return detail view for Designs."""
        return reverse("plugins:nautobot_design_builder:design", args=[self.pk])

    def __str__(self):
        """Stringify instance."""
        return self.name


class DesignInstanceQuerySet(RestrictedQuerySet):
    """Queryset for `DesignInstance` objects."""

    def get_by_natural_key(self, design_name, instance_name):
        """Get Design Instance by natural key."""
        return self.get(design__job__name=design_name, name=instance_name)


DESIGN_NAME_MAX_LENGTH = 100

DESIGN_OWNER_MAX_LENGTH = 100


@extras_features("statuses")
class DesignInstance(PrimaryModel, StatusModel):
    """Design instance represents the result of executing a design.

    Design instance represents the collection of Nautobot objects
    that have been created or updated as part of the execution of
    a design job. In this way, we can provide "services" that can
    be updated or removed at a later time.
    """

    # TODO: add version field to indicate which version of a design
    #       this instance is on. (future feature)
    design = models.ForeignKey(to=Design, on_delete=models.PROTECT, editable=False, related_name="instances")
    name = models.CharField(max_length=DESIGN_NAME_MAX_LENGTH)
    owner = models.CharField(max_length=DESIGN_OWNER_MAX_LENGTH, blank=True, null=True)
    first_implemented = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    last_implemented = models.DateTimeField(blank=True, null=True)
    live_state = StatusField(blank=False, null=False, on_delete=models.PROTECT)

    objects = DesignInstanceQuerySet.as_manager()

    class Meta:
        """Meta class."""

        constraints = [
            models.UniqueConstraint(
                fields=["design", "name"],
                name="unique_design_instances",
            ),
        ]
        unique_together = [
            ("design", "name"),
        ]

    def clean(self):
        """Guarantee that the design field cannot be changed."""
        super().clean()
        if not self._state.adding:
            enforce_managed_fields(self, ["design"], message="is a field that cannot be changed")

    def get_absolute_url(self):
        """Return detail view for design instances."""
        return reverse("plugins:nautobot_design_builder:designinstance", args=[self.pk])

    def __str__(self):
        """Stringify instance."""
        return f"{self.design.name} - {self.name}"

    def delete(self, *args, **kwargs):
        """Protect logic to remove Design Instance."""
        if not (
            self.status.name == choices.DesignInstanceStatusChoices.DECOMMISSIONED
            and self.live_state.name != choices.DesignInstanceLiveStateChoices.DEPLOYED
        ):
            raise ValidationError("A Design Instance can only be delete if it's Decommissioned and not Deployed.")
        return super().delete(*args, **kwargs)


class Journal(PrimaryModel):
    """The Journal represents a single execution of a design instance.

    A design instance will have a minimum of one journal. When the design
    is first implemented the journal is created and includes a list of
    all changes. If a design instance is re-run then the last input is
    used to run the job again. A new journal is created for each run
    after the first.

    In the future, the Journal will be used to provide idempotence for
    designs. However, we will need to implement an identifier strategy
    for every object within a design before that can happen.
    """

    design_instance = models.ForeignKey(to=DesignInstance, on_delete=models.CASCADE, editable=False)
    job_result = models.ForeignKey(to=JobResult, on_delete=models.PROTECT, editable=False)

    def get_absolute_url(self):
        """Return detail view for design instances."""
        return reverse("plugins:nautobot_design_builder:journal", args=[self.pk])

    @property
    def user_input(self):
        """Get the user input provided when the job was run.

        Returns:
            Dictionary of input data provided by the user. Note: the
            input values are deserialized from the job_result of the
            last run.
        """
        if nautobot_version < "2.0":
            user_input = self.job_result.job_kwargs.get("data", {}).copy()
        else:
            user_input = self.job_result.task_kwargs.copy()
        job = self.design_instance.design.job
        return job.job_class.deserialize_data(user_input)

    def log(self, model_instance):
        """Log changes to a model instance.

        This will log the differences between a model instance's
        initial state and its current state. If the model instance
        was previously updated during the life of the current journal
        than the comparison is made with the initial state when the
        object was logged in this journal.

        Args:
            model_instance: Model instance to log changes.
        """
        instance = model_instance.instance
        content_type = ContentType.objects.get_for_model(instance)
        try:
            entry = self.entries.get(
                _design_object_type=content_type,
                _design_object_id=instance.id,
            )
            # Look up the pre_change state from the existing
            # record and record the differences.
            entry.changes = model_instance.get_changes(entry.changes["pre_change"])
            entry.save()
        except JournalEntry.DoesNotExist:
            self.entries.create(
                _design_object_type=content_type,
                _design_object_id=instance.id,
                changes=model_instance.get_changes(),
                full_control=model_instance.created,
            )


class JournalEntry(PrimaryModel):
    """A single entry in the journal for exactly 1 object.

    The journal entry represents the changes that design builder
    made to a single object. The field changes are recorded in the
    `changes` attribute and the object that was changed can be
    accessed via the `design_object` attribute.If `full_control` is
    `True` then design builder created this object, otherwise
    design builder only updated the object.

    Args:
        PrimaryModel (_type_): _description_
    """

    journal = models.ForeignKey(
        to=Journal,
        on_delete=models.CASCADE,
        related_name="entries",
    )

    _design_object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        related_name="+",
        blank=False,
    )
    _design_object_id = models.UUIDField(blank=False)
    design_object = ct_fields.GenericForeignKey(ct_field="_design_object_type", fk_field="_design_object_id")
    changes = models.JSONField(encoder=NautobotKombuJSONEncoder, editable=False, null=True, blank=True)
    full_control = models.BooleanField(editable=False)

    def get_absolute_url(self):
        """Return detail view for design instances."""
        return reverse("plugins:nautobot_design_builder:journalentry", args=[self.pk])
