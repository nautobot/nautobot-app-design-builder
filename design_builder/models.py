from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import fields as ct_fields
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import models
from django.urls import reverse

from nautobot.apps.models import PrimaryModel
from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.extras.models import Job as JobModel, JobResult, StatusModel
from nautobot.extras.utils import extras_features
from nautobot.utilities.querysets import RestrictedQuerySet

from design_builder.util import nautobot_version


# TODO: this method needs to be put in the custom validators module.
# it will be used to enforce attributes managed by Design Builder
def enforce_managed_fields(new_model, field_names, message="is managed by Design Builder and cannot be changed."):
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

    def get_by_natural_key(self, name):
        return self.get(job__name=name)


@extras_features("statuses")
class Design(PrimaryModel, StatusModel):
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
        return self.job.name

    def get_absolute_url(self):
        """Return detail view for Designs."""
        return reverse("plugins:design_builder:design", args=[self.name])

    def __str__(self):
        """Stringify instance."""
        return self.name


class DesignInstanceQuerySet(RestrictedQuerySet):
    """Queryset for `DesignInstance` objects."""

    def get_by_natural_key(self, design_name, instance_name):
        return self.get(design__job__name=design_name, name=instance_name)


class DesignInstance(PrimaryModel):
    """Design instance represents the result of executing a design.

    Design instance represents the collection of Nautobot objects
    that have been created or updated as part of the execution of
    a design job. In this way, we can provide "services" that can
    be updated or removed at a later time.
    """

    # TODO: add version field to indicate which version of a design
    #       this instance is on. (future feature)
    design = models.ForeignKey(to=Design, on_delete=models.PROTECT, editable=False)
    name = models.CharField(max_length=100)
    owner = models.CharField(max_length=100)
    first_implemented = models.DateTimeField(blank=True, null=True)
    last_implemented = models.DateTimeField(blank=True, null=True)

    objects = DesignInstanceQuerySet.as_manager()

    class Meta:
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
        """Return detail view for Designs."""
        return reverse("plugins:design_builder:design", args=[self.design.name, self.name])

    def __str__(self):
        """Stringify instance."""
        return f"{self.design.name} - {self.name}"


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

    journal = models.ForeignKey(to=Journal, on_delete=models.CASCADE)
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
