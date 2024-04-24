"""Collection of models that DesignBuilder uses to track design implementations."""

import logging
from typing import List
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import fields as ct_fields
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import models
from django.dispatch import Signal
from django.urls import reverse

from nautobot.apps.models import PrimaryModel, BaseModel
from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.extras.models import Job as JobModel, JobResult, Status, StatusField, Tag
from nautobot.extras.utils import extras_features
from nautobot.utilities.querysets import RestrictedQuerySet
from nautobot.utilities.choices import ColorChoices

from .util import nautobot_version, get_created_and_last_updated_usernames_for_model
from . import choices
from .errors import DesignValidationError

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

    # TODO: Add saved graphql query (future feature)
    # TODO: Add a template mapping to get custom payload (future feature)
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

    @property
    def description(self):
        """Get the description from the Job."""
        if self.job.job_class and hasattr(self.job.job_class.Meta, "description"):
            return self.job.job_class.Meta.description
        return ""

    @property
    def version(self):
        """Get the version from the Job."""
        if self.job.job_class and hasattr(self.job.job_class.Meta, "version"):
            return self.job.job_class.Meta.version
        return ""

    @property
    def docs(self):
        """Get the docs from the Job."""
        if self.job.job_class and hasattr(self.job.job_class.Meta, "docs"):
            return self.job.job_class.Meta.docs
        return ""


class DesignInstanceQuerySet(RestrictedQuerySet):
    """Queryset for `DesignInstance` objects."""

    def get_by_natural_key(self, design_name, instance_name):
        """Get Design Instance by natural key."""
        return self.get(design__job__name=design_name, name=instance_name)


DESIGN_NAME_MAX_LENGTH = 255


@extras_features("statuses")
class DesignInstance(PrimaryModel):
    """Design instance represents the result of executing a design.

    Design instance represents the collection of Nautobot objects
    that have been created or updated as part of the execution of
    a design job. In this way, we can provide "services" that can
    be updated or removed at a later time.
    """

    pre_decommission = Signal()

    post_decommission = Signal()

    status = StatusField(blank=False, null=False, on_delete=models.PROTECT, related_name="design_instance_statuses")
    design = models.ForeignKey(to=Design, on_delete=models.PROTECT, editable=False, related_name="instances")
    name = models.CharField(max_length=DESIGN_NAME_MAX_LENGTH)
    first_implemented = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    last_implemented = models.DateTimeField(blank=True, null=True)
    live_state = StatusField(blank=False, null=False, on_delete=models.PROTECT)
    version = models.CharField(max_length=20, blank=True, default="")

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
        verbose_name = "Design Deployment"
        verbose_name_plural = "Design Deployments"

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

    def decommission(self, *object_ids, local_logger=logger):
        """Decommission a design instance.

        This will reverse the journal entries for the design instance and
        reset associated objects to their pre-design state.
        """
        if not object_ids:
            local_logger.info("Decommissioning design", extra={"obj": self})
            self.__class__.pre_decommission.send(self.__class__, design_instance=self)
        # Iterate the journals in reverse order (most recent first) and
        # revert each journal.
        for journal in self.journals.filter(active=True).order_by("-last_updated"):
            journal.revert(*object_ids, local_logger=local_logger)

        if not object_ids:
            content_type = ContentType.objects.get_for_model(DesignInstance)
            self.status = Status.objects.get(
                content_types=content_type, name=choices.DesignInstanceStatusChoices.DECOMMISSIONED
            )
            self.save()
            self.__class__.post_decommission.send(self.__class__, design_instance=self)

    def delete(self, *args, **kwargs):
        """Protect logic to remove Design Instance."""
        if not (
            self.status.name == choices.DesignInstanceStatusChoices.DECOMMISSIONED
            and self.live_state.name != choices.DesignInstanceLiveStateChoices.DEPLOYED
        ):
            raise ValidationError("A Design Instance can only be delete if it's Decommissioned and not Deployed.")
        return super().delete(*args, **kwargs)

    @property
    def created_by(self):
        """Get the username of the user who created the object."""
        # TODO: if we just add a "created_by" and "last_updated_by" field, doesn't that
        # reduce the complexity of code that we have in the util module?
        created_by, _ = get_created_and_last_updated_usernames_for_model(self)
        return created_by

    @property
    def last_updated_by(self):
        """Get the username of the user who update the object last time."""
        _, last_updated_by = get_created_and_last_updated_usernames_for_model(self)
        return last_updated_by


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

    design_instance = models.ForeignKey(
        to=DesignInstance,
        on_delete=models.CASCADE,
        editable=False,
        related_name="journals",
    )
    job_result = models.ForeignKey(to=JobResult, on_delete=models.PROTECT, editable=False)
    builder_output = models.JSONField(encoder=NautobotKombuJSONEncoder, editable=False, null=True, blank=True)
    active = models.BooleanField(editable=False, default=True)

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
                full_control=model_instance.metadata.created,
            )
        return entry

    def revert(self, *object_ids, local_logger: logging.Logger = logger):
        """Revert the changes represented in this Journal.

        Raises:
            ValueError: the error will include the trace from the original exception.
        """
        # TODO: In what case is _design_object_id not set? I know we have `blank=True`
        # in the foreign key constraints, but I don't know when that would ever
        # happen and whether or not we should perhaps always require a design_object.
        # Without a design object we cannot have changes, right? I suppose if the
        # object has been deleted since the change was made then it wouldn't exist,
        # but I think we need to discuss the implications of this further.
        entries = self.entries.order_by("-last_updated").exclude(_design_object_id=None).exclude(active=False)
        if not object_ids:
            local_logger.info("Reverting journal", extra={"obj": self})
        else:
            entries = entries.filter(_design_object_id__in=object_ids)

        for journal_entry in entries:
            try:
                journal_entry.revert(local_logger=local_logger)
            except (ValidationError, DesignValidationError) as ex:
                local_logger.error(str(ex), extra={"obj": journal_entry.design_object})
                raise ValueError from ex

        if not object_ids:
            # When the Journal is reverted, we mark is as not active anymore
            self.active = False
            self.save()

    def __sub__(self, other: "Journal"):
        """Calculate the difference between two journals.

        This method calculates the differences between the journal entries of two
        journals. This is similar to Python's `set.difference` method. The result
        is a queryset of JournalEntries from this journal that represent objects
        that are are not in the `other` journal.

        Args:
            other (Journal): The other Journal to subtract from this journal.

        Returns:
            Queryset of journal entries
        """
        if other is None:
            return []

        other_ids = other.entries.values_list("_design_object_id")

        return (
            self.entries.order_by("-last_updated")
            .exclude(_design_object_id__in=other_ids)
            .values_list("_design_object_id", flat=True)
        )


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

    def filter_same_parent_design_instance(self, entry: "JournalEntry"):
        """Returns JournalEntries which have the same parent design instance."""
        return self.filter(_design_object_id=entry._design_object_id).exclude(  # pylint: disable=protected-access
            journal__design_instance__id=entry.journal.design_instance.id
        )


class JournalEntry(BaseModel):
    """A single entry in the journal for exactly 1 object.

    The journal entry represents the changes that design builder
    made to a single object. The field changes are recorded in the
    `changes` attribute and the object that was changed can be
    accessed via the `design_object` attribute.If `full_control` is
    `True` then design builder created this object, otherwise
    design builder only updated the object.
    """

    objects = JournalEntryQuerySet.as_manager()

    created = models.DateField(auto_now_add=True, null=True)

    last_updated = models.DateTimeField(auto_now=True, null=True)

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
    active = models.BooleanField(editable=False, default=True)

    def get_absolute_url(self):
        """Return detail view for design instances."""
        return reverse("plugins:nautobot_design_builder:journalentry", args=[self.pk])

    @staticmethod
    def update_current_value_from_dict(current_value, added_value, removed_value):
        """Update current value if it's a dictionary."""
        keys_to_remove = []
        for key in current_value:
            if key in added_value:
                if key in removed_value:
                    current_value[key] = removed_value[key]
                else:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del current_value[key]

        # Recovering old values that the JournalEntry deleted.
        for key in removed_value:
            if key not in added_value:
                current_value[key] = removed_value[key]

    def revert(self, local_logger: logging.Logger = logger):  # pylint: disable=too-many-branches
        """Revert the changes that are represented in this journal entry.

        Raises:
            ValidationError: the error will include all of the managed fields that have
            changed.
            DesignValidationError: when the design object is referenced by other active Journals.

        """
        if not self.design_object:
            # This is something that may happen when a design has been updated and object was deleted
            return

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

        local_logger.info("Reverting journal entry for %s %s", object_type, object_str, extra={"obj": self})
        if self.full_control:
            related_entries = (
                JournalEntry.objects.filter(active=True)
                .filter_related(self)
                .filter_same_parent_design_instance(self)
                .exclude_decommissioned()
            )
            if related_entries:
                active_journal_ids = ",".join([str(j.id) for j in related_entries])
                raise DesignValidationError(f"This object is referenced by other active Journals: {active_journal_ids}")

            self.design_object._current_design = self.journal.design_instance  # pylint: disable=protected-access
            self.design_object.delete()
            local_logger.info("%s %s has been deleted as it was owned by this design", object_type, object_str)
        else:
            if not self.changes:
                local_logger.info("No changes found in the Journal Entry.")
                return

            if "differences" not in self.changes:
                # TODO: We should probably change the `changes` dictionary to
                # a concrete class so that our static analysis tools can catch
                # problems like this.
                local_logger.error("`differences` key not present.")
                return

            differences = self.changes["differences"]
            for attribute in differences.get("added", {}):
                added_value = differences["added"][attribute]
                if differences["removed"]:
                    removed_value = differences["removed"][attribute]
                else:
                    removed_value = None
                if isinstance(added_value, dict) and isinstance(removed_value, dict):
                    # If the value is a dictionary (e.g., config context), we only update the
                    # keys changed, honouring the current value of the attribute
                    current_value = getattr(self.design_object, attribute)
                    current_value_type = type(current_value)
                    if isinstance(current_value, dict):
                        self.update_current_value_from_dict(
                            current_value=current_value,
                            added_value=added_value,
                            removed_value=removed_value,
                        )
                    elif isinstance(current_value, models.Model):
                        # The attribute is a Foreign Key that is represented as a dict
                        try:
                            current_value = current_value_type.objects.get(id=removed_value["id"])
                        except ObjectDoesNotExist:
                            current_value = None
                    elif current_value is None:
                        pass
                    else:
                        # TODO: cover other use cases, such as M2M relationship
                        local_logger.error(
                            "%s can't be reverted because decommission of type %s is not supported yet.",
                            current_value,
                            current_value_type,
                        )

                    setattr(self.design_object, attribute, current_value)
                elif differences["removed"] is not None:
                    try:
                        setattr(self.design_object, attribute, removed_value)
                    except AttributeError:
                        # TODO: the current serialization (serialize_object_v2) doesn't exclude properties
                        local_logger.debug(
                            "Attribute %s in this object %s can't be set. It may be a 'property'.",
                            attribute,
                            object_str,
                            extra={"obj": self.design_object},
                        )

                self.design_object.save()
                local_logger.info(
                    "%s %s has been reverted to its previous state.",
                    object_type,
                    object_str,
                    extra={"obj": self.design_object},
                )

        self.active = False
        self.save()
