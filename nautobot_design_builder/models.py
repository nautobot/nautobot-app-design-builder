"""Collection of models that DesignBuilder uses to track design implementations."""
import logging
from typing import List
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import fields as ct_fields
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import models
from django.urls import reverse

from nautobot.apps.models import PrimaryModel
from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.extras.models import Job as JobModel, JobResult, StatusModel, StatusField, Tag
from nautobot.extras.utils import extras_features
from nautobot.utilities.querysets import RestrictedQuerySet
from nautobot.utilities.choices import ColorChoices

from .util import nautobot_version
from . import choices

logger = logging.getLogger(__name__)


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
            user_input = self.job_result.task_kwargs.copy()  # pylint: disable=no-member
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

        if model_instance.created:
            try:
                tag_design_builder, _ = Tag.objects.get_or_create(
                    name=f"Managed by {self.design_instance}",
                    defaults={
                        "description": f"Managed by Design Builder: {self.design_instance}",
                        "color": ColorChoices.COLOR_LIGHT_GREEN,
                    },
                )
                instance.tags.add(tag_design_builder)
                instance.save()
            except AttributeError:
                # This happens when the instance doesn't support Tags, for example Region
                pass

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
            entry = self.entries.create(
                _design_object_type=content_type,
                _design_object_id=instance.id,
                changes=model_instance.get_changes(),
                full_control=model_instance.created,
            )
        return entry

    def revert(self, local_logger: logging.Logger = logger):
        """Revert the changes represented in this Journal.

        Raises:
            ValidationError: _description_

        Returns:
            _type_: _description_
        """
        # TODO: In what case is _design_object_id not set? I know we have `blank=True`
        # in the foreign key constraints, but I don't know when that would ever
        # happen and whether or not we should perhaps always require a design_object.
        # Without a design object we cannot have changes, right? I suppose if the
        # object has been deleted since the change was made then it wouldn't exist,
        # but I think we need to discuss the implications of this further.
        for journal_entry in self.entries.exclude(_design_object_id=None).order_by("-last_updated"):
            try:
                journal_entry.revert(local_logger=local_logger)
            except ValidationError as ex:
                local_logger.error(str(ex), extra={"obj": journal_entry.design_object})
                raise ValueError(ex)


class JournalEntryQuerySet(RestrictedQuerySet):
    """Queryset for `JournalEntry` objects."""

    def exclude_decommissioned(self):
        """Returns JournalEntry which the related DesignInstance is not decommissioned."""
        return self.exclude(journal__design_instance__status__name=choices.DesignInstanceStatusChoices.DECOMMISSIONED)

    def filter_related(self, entry: "JournalEntry"):
        """Returns JournalEntries which have the same object ID but excluding itself."""
        return self.filter(_design_object_id=entry._design_object_id).exclude(  # pylint: disable=protected-access
            id=entry.id
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

    objects = JournalEntryQuerySet.as_manager()

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

    # TODO: adding to refactor later
    # pylint: disable=too-many-nested-blocks,too-many-branches
    def revert(self, local_logger: logging.Logger = logger):
        """Revert the changes that are represented in this journal entry."""
        if not self.design_object:
            raise ValidationError("No reference object found for this JournalEntry.")

        # It is possible that the journal entry contains a stale copy of the
        # design object. Consider this example: A journal entry is create and
        # kept in memory. The object it represents is changed in another area
        # of code, but using a different in-memory object. The in-memory copy
        # of the journal entry's `design_object` is now no-longer representative
        # of the actual database state. Since we need to know the current state
        # of the design object, the only way to be sure of this is to
        # refresh our copy.
        self.design_object.refresh_from_db()
        object_type = self.design_object._meta.verbose_name.title()
        object_str = str(self.design_object)
        if self.full_control:
            related_entries = JournalEntry.objects.filter_related(self).exclude_decommissioned()
            if related_entries:
                # TODO: Should this be a `DesignValidationError` or even a more specific
                # error, such as `CrossReferenceError`?
                raise ValidationError("This object is referenced by other active Journals")

            self.design_object.delete()
            local_logger.info("%s %s has been deleted as it was owned by this design", object_type, object_str)
        else:
            # TODO: Is this really an error condition? Nothing can be done, but
            # also, nothing needs to be done. If nothing was changed then reverting
            # means nothing will change... it's like a NOOP, but is that an error?
            if not self.changes:
                raise ValidationError("No changes found in the Journal Entry.")

            if "differences" not in self.changes:
                # TODO: This error message is going to have very little
                # meaning to an end user. If we get to this point then
                # there is actually a programming error, since we always
                # set the `differences` key in the changes dictionary (at least
                # I think that's the case)
                #
                # We should probably change the `changes` dictionary to
                # a concrete class so that our static analysis tools can catch
                # problems like this.
                raise ValidationError("`differences` key not present.")

            differences = self.changes["differences"]

            for attribute in differences.get("added", {}):
                value_changed = differences["added"][attribute]
                old_value = differences["removed"][attribute]
                if isinstance(value_changed, dict):
                    # If the value is a dictionary (e.g., config context), we only update the
                    # keys changed, honouring the current value of the attribute
                    current_value = getattr(self.design_object, attribute)
                    keys_to_remove = []
                    for key in current_value:
                        if key in value_changed:
                            if key in old_value:
                                current_value[key] = old_value[key]
                            else:
                                keys_to_remove.append(key)

                    # Recovering old values that the JournalEntry deleted.
                    for key in old_value:
                        if key not in value_changed:
                            current_value[key] = old_value[key]

                    for key in keys_to_remove:
                        del current_value[key]
                    setattr(self.design_object, attribute, current_value)
                else:
                    setattr(self.design_object, attribute, old_value)

                self.design_object.save()
                local_logger.info(
                    "%s %s has been reverted to its previous state.",
                    object_type,
                    object_str,
                    extra={"obj": self.design_object},
                )
