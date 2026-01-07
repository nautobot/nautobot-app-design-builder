"""Design Builder custom validators to protect refernced objects."""

from django.apps import apps
from django.conf import settings
from django.db.models import ProtectedError
from django.db.models.signals import pre_delete
from nautobot.apps.models import CustomValidator
from nautobot.extras.registry import registry

from nautobot_design_builder.middleware import GlobalRequestMiddleware
from nautobot_design_builder.models import ChangeRecord


def validate_delete(instance, **kwargs):
    """Prevent an object associated with a deployment from deletion."""
    request = GlobalRequestMiddleware.get_current_request()
    if (
        request
        and settings.PLUGINS_CONFIG["nautobot_design_builder"]["protected_superuser_bypass"]
        and request.user.is_superuser
    ):
        return

    # TODO: We use this logic here as well as in the custom validator. I think
    # it may be useful to extract it into the ChangeRecordQuerySet
    change_record = (
        ChangeRecord.objects.filter(_design_object_id=instance.id, active=True).exclude_decommissioned().first()
    )
    if change_record is None:
        return
    if change_record.change_set.deployment == getattr(instance, "_current_deployment", None):
        if change_record.full_control:
            return
    # The next couple of lines need some explanation... due to the way
    # Django tests run, an exception is caused during unit tests when
    # an exception has been raised and then a query takes place. When we
    # raise the ProtectedError here the dispatch method catches it and
    # produces an error message, which includes the string representation
    # of the protected_objects. This string representation ultimately causes
    # a lookup for the job name (since the design name is the job name).
    # This lookup then causes a new transaction error and the test fails. In
    # order to prevent this, we're going to prime the lookups before we
    # raise the exception.
    design = change_record.change_set.deployment.design
    design.name  # pylint:disable=pointless-statement

    # Only prevent deletion if we do *not* have full control
    raise ProtectedError("A design instance owns this object.", set([design]))


class BaseValidator(CustomValidator):
    """Base CustomValidator class that implements the core logic for enforcing validation rules defined in this app."""

    model = None

    @classmethod
    def factory(cls, app_label, model):
        """Create a new validator class for the app_label/model combination.

        This factory dynamically creates a custom validator for a given model. The
        validator's parent class is
        """
        model_class = apps.get_model(app_label=app_label, model_name=model)
        pre_delete.connect(validate_delete, sender=model_class)
        return type(
            f"{app_label.capitalize()}{model.capitalize()}CustomValidator",
            (BaseValidator,),
            {"model": f"{app_label}.{model}"},
        )

    @classmethod
    def disconnect(cls):
        """Disconnect the pre_delete handler for this model."""
        pre_delete.disconnect(validate_delete, sender=cls.model)

    def clean(self):
        """The clean method executes the actual rule enforcement logic for each model.

        1) If an object was created by a design, then all of the attributes set in that
        deployment are owned by that design. The only time that set of attributes can be
        updated is when the design is re-run for the same deployment.

        2) If an object was just updated, then only those attributes that were set during the
        execution of the deployment are protected. Updates outside of the design cannot change
        those attributes.

        3) If an object is a dictionary (such as a config context) then the protection goes
        one layer down and includes keys on the dictionary.
        """
        errors = {}
        request = GlobalRequestMiddleware.get_current_request()
        if (
            request
            and settings.PLUGINS_CONFIG["nautobot_design_builder"]["protected_superuser_bypass"]
            and request.user.is_superuser
        ):
            return
        obj = self.context["object"]
        obj_class = obj.__class__

        # If it's a create operation there is nothing to protect against
        if not obj.present_in_database:
            return

        existing_object = obj_class.objects.get(id=obj.id)
        for record in ChangeRecord.objects.filter(  # pylint: disable=too-many-nested-blocks
            _design_object_id=obj.id, active=True
        ).exclude_decommissioned():
            for attribute in record.changes:
                new_value = getattr(obj, attribute)
                old_value = getattr(existing_object, attribute)
                if new_value != old_value:
                    error_context = ""
                    # For dict attributes (i.e., JSON fields), the design builder can own only a few keys
                    if isinstance(old_value, dict):
                        for key, value in record.changes[attribute]["new_value"].items():
                            if new_value[key] != value:
                                error_context = f"Key {key}"
                                break
                        else:
                            # If all the referenced attributes are not changing, we can update it
                            # TODO: This can't be correct, if a dictionary is the changed value returned
                            # then we wouldn't even check the rest. I think is supposed to be a continue
                            return

                    # If the update is an update of the owning deployment, then allow the change.
                    if getattr(obj, "_current_deployment", None) == record.change_set.deployment:
                        continue

                    # This next bit handles correcting the field name (for form errors)
                    # when the field is a relation and the attribute is the foreign-key
                    # field
                    field = obj_class._meta.get_field(attribute)
                    errors[field.name] = (
                        f"The attribute is managed by the Design Instance: {record.change_set.deployment}. {error_context}"
                    )

        if errors:
            self.validation_error(errors)


class CustomValidatorIterator:  # pylint: disable=too-few-public-methods
    """Iterator that generates CustomValidator classes for each model registered in the extras feature query registry 'custom_validators'."""

    def __iter__(self):
        """Return a generator of CustomValidator classes for each registered model."""
        for app_label, models in registry["model_features"]["custom_validators"].items():
            for model in models:
                if (app_label, model) in settings.PLUGINS_CONFIG["nautobot_design_builder"]["protected_models"]:
                    cls = BaseValidator.factory(app_label, model)
                    yield cls


custom_validators = CustomValidatorIterator()
