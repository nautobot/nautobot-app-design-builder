"""Logic used to track changes and change logging."""

from contextlib import contextmanager
from typing import TYPE_CHECKING

from django.db import models as django_models

if TYPE_CHECKING:
    from nautobot_design_builder.design import ModelInstance


def _get_change_value(value):
    if isinstance(value, django_models.Manager):
        value = {item.pk for item in value.all()}
    return value


@contextmanager
def change_log(model_instance: "ModelInstance", attr_name: str):
    """Log changes for a field.

    This context manager will record the value of a field prior to a change
    as well as the value after the change. If the values are different then
    a change record is added to the underlying model instance.

    Args:
        model_instance (ModelInstance): The model instance that is being updated.
        attr_name (str): The attribute to be updated.
    """
    old_value = _get_change_value(getattr(model_instance.design_instance, attr_name))
    yield
    new_value = _get_change_value(getattr(model_instance.design_instance, attr_name))
    if old_value != new_value:
        if isinstance(old_value, set):
            model_instance.design_metadata.changes[attr_name] = {
                "old_items": old_value,
                "new_items": new_value,
            }
            # Many-to-Many changes need to be logged on the parent,
            # and this won't happen implicitly so we log the changes
            # explicitly here.
            #
            # TODO: This has been commented out because I *think* that it is
            # no longer needed since their is now a journal log created in the
            # create_child method.
            # model_instance.design_metadata.environment.journal.log(model_instance)
        else:
            model_instance.design_metadata.changes[attr_name] = {
                "old_value": old_value,
                "new_value": new_value,
            }


def revert_changed_dict(current_value: dict, original_value: dict, changed_value: dict) -> dict:
    """Create a new dictionary that correctly returns a changed dictionary to its expected value.

    In many cases Nautobot model object have dictionary attributes (configuration contexts, secret
    params, etc). The design builder will attempt to revert design related attributes within
    these dictionaries. Any dictionary items changed by the design will be reverted to their original
    value and any items added outside of the process will be left alone. Dictionary items added
    by the design wil be removed.

    Args:
        current_value (dict): The dictionary value as it is right now.
        original_value (dict): The dictionary value before the change.
        changed_value (dict): The dictionary value after the change.

    Returns:
        dict: The dictionary as we expect it to be without the design changes.
    """
    original_keys = set(original_value.keys())
    changed_keys = set(changed_value.keys())
    current_keys = set(current_value.keys())
    design_keys = changed_keys.union(original_keys)
    return {**{key: current_value[key] for key in current_keys.difference(design_keys)}, **original_value}
