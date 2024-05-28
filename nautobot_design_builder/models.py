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
from nautobot.extras.models import Job as JobModel, JobResult, Status, StatusField
from nautobot.extras.utils import extras_features
from nautobot.utilities.querysets import RestrictedQuerySet

from .util import get_created_and_last_updated_usernames_for_model
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

    Design may or may not have any deployments (implementations), but
    is available for execution. It is largely a one-to-one type
    relationship with Job, but will only exist if the Job has a
    DesignJob in its ancestry.

    Deployments of the Design model are created automatically from
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

    @property
    def design_mode(self):
        """Determine the implementation mode for the design."""
        if self.job.job_class:
            return self.job.job_class.design_mode()
        return None

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


class DeploymentQuerySet(RestrictedQuerySet):
    """Queryset for `Deployment` objects."""

    def get_by_natural_key(self, design_name, deployment_name):
        """Get a Deployment by its natural key."""
        return self.get(design__job__name=design_name, name=deployment_name)


DESIGN_NAME_MAX_LENGTH = 255


@extras_features("statuses")
class Deployment(PrimaryModel):
    """A Deployment represents the result of executing a design.

    A Deployment represents the collection of Nautobot objects
    that have been created or updated as part of the execution of
    a design job. In this way, we can provide "services" that can
    be updated or removed at a later time.
    """

    pre_decommission = Signal()

    post_decommission = Signal()

    status = StatusField(blank=False, null=False, on_delete=models.PROTECT, related_name="deployment_statuses")
    design = models.ForeignKey(to=Design, on_delete=models.PROTECT, editable=False, related_name="deployments")
    name = models.CharField(max_length=DESIGN_NAME_MAX_LENGTH)
    first_implemented = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    last_implemented = models.DateTimeField(blank=True, null=True)
    version = models.CharField(max_length=20, blank=True, default="")

    objects = DeploymentQuerySet.as_manager()

    class Meta:
        """Meta class."""

        constraints = [
            models.UniqueConstraint(
                fields=["design", "name"],
                name="unique_deployments",
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
        """Return detail view for design deployments."""
        return reverse("plugins:nautobot_design_builder:deployment", args=[self.pk])

    def __str__(self):
        """Stringify instance."""
        return f"{self.design.name} - {self.name}"

    def decommission(self, *object_ids, local_logger=logger):
        """Decommission a design instance.

        This will reverse the change records for the design instance and
        reset associated objects to their pre-design state.
        """
        if not object_ids:
            local_logger.info("Decommissioning design", extra={"obj": self})
            self.__class__.pre_decommission.send(self.__class__, deployment=self)
        # Iterate the change sets in reverse order (most recent first) and
        # revert each change set.
        for change_set in self.change_sets.filter(active=True).order_by("-last_updated"):
            change_set.revert(*object_ids, local_logger=local_logger)

        if not object_ids:
            content_type = ContentType.objects.get_for_model(Deployment)
            self.status = Status.objects.get(
                content_types=content_type, name=choices.DeploymentStatusChoices.DECOMMISSIONED
            )
            self.save()
            self.__class__.post_decommission.send(self.__class__, deployment=self)

    def delete(self, *args, **kwargs):
        """Protect logic to remove Design Instance."""
        if not self.status.name == choices.DeploymentStatusChoices.DECOMMISSIONED:
            raise ValidationError("A Design Instance can only be delete if it's Decommissioned.")
        return super().delete(*args, **kwargs)

    def get_design_objects(self, model):
        """Get all of the design objects for this design instance that are of `model` type.

        For instance, do get all of the `dcim.Interface` objects for this design instance call
        `deployment.get_design_objects(Interface)`.

        Args:
            model (type): The model type to match.

        Returns:
            Queryset of matching objects.
        """
        records = ChangeRecord.objects.filter_by_deployment(self, model=model)
        return model.objects.filter(pk__in=records.values_list("_design_object_id", flat=True))

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


class ChangeSet(PrimaryModel):
    """The ChangeSet represents a single execution of a design instance.

    A design instance will have a minimum of one change set. When the design
    is first implemented the change set is created and includes a list of
    all changes. If a design instance is re-run then the last input is
    used to run the job again. A new change set is created for each run
    after the first.

    In the future, the ChangeSet will be used to provide idempotence for
    designs. However, we will need to implement an identifier strategy
    for every object within a design before that can happen.
    """

    deployment = models.ForeignKey(
        to=Deployment,
        on_delete=models.CASCADE,
        editable=False,
        related_name="change_sets",
    )
    job_result = models.OneToOneField(to=JobResult, on_delete=models.PROTECT, editable=False)
    active = models.BooleanField(editable=False, default=True)

    class Meta:
        """Set the default query ordering."""

        ordering = ["-last_updated"]

    def get_absolute_url(self):
        """Return detail view for changeset."""
        return reverse("plugins:nautobot_design_builder:changeset", args=[self.pk])

    @property
    def user_input(self):
        """Get the user input provided when the job was run.

        Returns:
            Dictionary of input data provided by the user. Note: the
            input values are deserialized from the job_result of the
            last run.
        """
        user_input = self.job_result.job_kwargs.get("data", {}).copy()
        job = self.deployment.design.job
        return job.job_class.deserialize_data(user_input)

    def _next_index(self):
        # The hokey getting/setting here is to make pylint happy
        # and not complain about `no-member`
        index = getattr(self, "_index", None)
        if index is None:
            index = self.records.aggregate(index=models.Max("index"))["index"]
            if index is None:
                index = -1
        index += 1
        setattr(self, "_index", index)
        return index

    def log(self, model_instance):
        """Log changes to a model instance.

        This will log the differences between a model instance's
        initial state and its current state. If the model instance
        was previously updated during the life of the current change set
        than the comparison is made with the initial state when the
        object was logged in this change set.

        Args:
            model_instance: Model instance to log changes.
        """
        instance = model_instance.instance
        content_type = ContentType.objects.get_for_model(instance)

        try:
            entry = self.records.get(
                _design_object_type=content_type,
                _design_object_id=instance.id,
            )
            # Look up the pre_change state from the existing
            # record and record the differences.
            entry.changes.update(model_instance.metadata.changes)
            entry.save()
        except ChangeRecord.DoesNotExist:
            entry = self.records.create(
                _design_object_type=content_type,
                _design_object_id=instance.id,
                changes=model_instance.metadata.changes,
                full_control=model_instance.metadata.created,
                index=self._next_index(),
            )
        return entry

    def revert(self, *object_ids, local_logger: logging.Logger = logger):
        """Revert the changes represented in this ChangeSet.

        Raises:
            ValueError: the error will include the trace from the original exception.
        """
        # TODO: In what case is _design_object_id not set? I know we have `blank=True`
        # in the foreign key constraints, but I don't know when that would ever
        # happen and whether or not we should perhaps always require a design_object.
        # Without a design object we cannot have changes, right? I suppose if the
        # object has been deleted since the change was made then it wouldn't exist,
        # but I think we need to discuss the implications of this further.
        records = self.records.order_by("-index").exclude(_design_object_id=None).exclude(active=False)
        if not object_ids:
            local_logger.info("Reverting change set", extra={"obj": self})
        else:
            records = records.filter(_design_object_id__in=object_ids)

        for record in records:
            try:
                record.revert(local_logger=local_logger)
            except (ValidationError, DesignValidationError) as ex:
                local_logger.error(str(ex), extra={"obj": record.design_object})
                raise ValueError from ex

        if not object_ids:
            # When the change set is reverted, we mark is as not active anymore
            self.active = False
            self.save()

    def __sub__(self, other: "ChangeSet"):
        """Calculate the difference between two change sets.

        This method calculates the differences between the records of two
        change sets. This is similar to Python's `set.difference` method. The result
        is a queryset of ChangeRecords from this change set that represent objects
        that are are not in the `other` change set.

        Args:
            other (ChangeSet): The other ChangeSet to subtract from this change set.

        Returns:
            Queryset of change records
        """
        if other is None:
            return []

        other_ids = other.records.values_list("_design_object_id")

        return (
            self.records.order_by("-index")
            .exclude(_design_object_id__in=other_ids)
            .values_list("_design_object_id", flat=True)
        )


class ChangeRecordQuerySet(RestrictedQuerySet):
    """Queryset for `ChangeRecord` objects."""

    def exclude_decommissioned(self):
        """Returns a ChangeRecord queryset which the related Deployment is not decommissioned."""
        return self.exclude(change_set__deployment__status__name=choices.DeploymentStatusChoices.DECOMMISSIONED)

    def filter_related(self, entry):
        """Returns other ChangeRecords which have the same object ID but are in different designs.

        Args:
            entry (ChangeRecord): The ChangeRecord to use as reference.

        Returns:
            QuerySet: The queryset that matches other change records with the same design object ID. This
            excludes matching records in the same design.
        """
        return (
            self.filter(active=True)
            .filter(_design_object_id=entry._design_object_id)  # pylint:disable=protected-access
            .exclude(change_set__deployment_id=entry.change_set.deployment_id)
        )

    def filter_by_deployment(self, deployment: "Deployment", model=None):
        """Lookup all the records for a design instance an optional model type.

        Args:
            deployment (Deployment): The design instance to retrieve all of the change records.
            model (type, optional): An optional model type to filter by. Defaults to None.

        Returns:
            Query set matching the options.
        """
        queryset = self.filter(change_set__deployment=deployment)
        if model:
            queryset.filter(_design_object_type=ContentType.objects.get_for_model(model))
        return queryset

    def design_objects(self, deployment: "Deployment"):
        """Get a set of change records for unique design objects.

        This method returns a queryset of change records for a deployment. However, rather
        than all of the change records, it will select only one change record for
        each distinct design object. This is useful to get the active objects for
        a given deployment.

        Args:
            deployment (Deployment): The deployment to get design objects.

        Returns:
            Queryset of change records with uniq design objects.
        """
        # This would all be much easier if we could just use a distinct on
        # fields. Unfortunately, MySQL doesn't support distinct on columns
        # so we have to kind of do it ourselves with the following application
        # logic.
        design_objects = (
            self.filter_by_deployment(deployment)
            .filter(active=True)
            .values_list("id", "_design_object_id", "_design_object_type")
        )
        design_object_ids = {
            f"{design_object_type}:{design_object_id}": record_id
            for record_id, design_object_id, design_object_type in design_objects
        }
        return self.filter(id__in=design_object_ids.values())


class ChangeRecord(BaseModel):
    """A single entry in the change set for exactly 1 object.

    The change record represents the changes that design builder
    made to a single object. The field changes are recorded in the
    `changes` attribute and the object that was changed can be
    accessed via the `design_object` attribute.If `full_control` is
    `True` then design builder created this object, otherwise
    design builder only updated the object.
    """

    objects = ChangeRecordQuerySet.as_manager()

    created = models.DateField(auto_now_add=True, null=True)

    last_updated = models.DateTimeField(auto_now=True, null=True)

    change_set = models.ForeignKey(
        to=ChangeSet,
        on_delete=models.CASCADE,
        related_name="records",
    )

    index = models.IntegerField(null=False, blank=False)

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

    class Meta:  # noqa:D106
        unique_together = [
            ("change_set", "index"),
            ("change_set", "_design_object_type", "_design_object_id"),
        ]

    def get_absolute_url(self):
        """Return detail view for design change record."""
        return reverse("plugins:nautobot_design_builder:changerecord", args=[self.pk])

    @staticmethod
    def update_current_value_from_dict(current_value, added_value, removed_value):
        """Update current value if it's a dictionary.

        The removed_value keys (the original one) are going to be recovered, the added_value ones
        will be reverted, and the current_value ones that were not added by the design will be kept.
        """
        keys_to_remove = []
        for key in current_value:
            if key in added_value:
                if key in removed_value:
                    # Reverting the value of keys that existed before and the design deployment modified
                    current_value[key] = removed_value[key]
                else:
                    keys_to_remove.append(key)

        # Removing keys that were added by the design.
        for key in keys_to_remove:
            del current_value[key]

        # Recovering old keys that the ChangeRecord deleted.
        for key in removed_value:
            if key not in added_value:
                current_value[key] = removed_value[key]

    def revert(self, local_logger: logging.Logger = logger):  # pylint: disable=too-many-branches
        """Revert the changes that are represented in this change record.

        Raises:
            ValidationError: the error will include all of the managed fields that have
            changed.
            DesignValidationError: when the design object is referenced by other active change sets.

        """
        if self.design_object is None:
            # This is something that may happen when a design has been updated and object was deleted
            return

        # It is possible that the change record contains a stale copy of the
        # design object. Consider this example: A change record is create and
        # kept in memory. The object it represents is changed in another area
        # of code, but using a different in-memory object. The in-memory copy
        # of the change record's `design_object` is now no-longer representative
        # of the actual database state. Since we need to know the current state
        # of the design object, the only way to be sure of this is to
        # refresh our copy.
        self.design_object.refresh_from_db()
        object_type = self.design_object._meta.verbose_name.title()
        object_str = str(self.design_object)

        local_logger.info("Reverting change record", extra={"obj": self.design_object})
        if self.full_control:
            related_records = ChangeRecord.objects.filter_related(self)
            if related_records.count() > 0:
                active_record_ids = ",".join(map(lambda entry: str(entry.id), related_records))
                raise DesignValidationError(
                    f"This object is referenced by other active ChangeSets: {active_record_ids}"
                )

            # The _current_deployment attribute is essentially a signal to our
            # pre-delete handler letting it know to forgo the protections for
            # deletion since this delete operation is part of an owning design.
            self.design_object._current_deployment = self.change_set.deployment  # pylint: disable=protected-access
            self.design_object.delete()
            local_logger.info("%s %s has been deleted as it was owned by this design", object_type, object_str)
        else:
            for attr_name, change in self.changes.items():
                current_value = getattr(self.design_object, attr_name)
                if "old_items" in change:
                    old_items = set(change["old_items"])
                    new_items = set(change["new_items"])
                    added_items = new_items - old_items
                    current_items = {item.pk for item in current_value.all()}
                    current_items -= added_items
                    current_value.set(current_value.filter(pk__in=current_items))
                else:
                    old_value = change["old_value"]
                    new_value = change["new_value"]

                    if isinstance(old_value, dict):
                        # config-context like thing, only change the keys
                        # that were added/changed
                        self.update_current_value_from_dict(
                            current_value=current_value,
                            added_value=new_value,
                            removed_value=old_value if old_value else {},
                        )
                    else:
                        setattr(self.design_object, attr_name, old_value)

                self.design_object.save()
                local_logger.info(
                    "%s %s has been reverted to its previous state.",
                    object_type,
                    object_str,
                    extra={"obj": self.design_object},
                )

        self.active = False
        self.save()
