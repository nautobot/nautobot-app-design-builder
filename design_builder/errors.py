"""Module containing error Exception classes specific to Design Builder."""
from collections import defaultdict
from inspect import isclass

from django.core.exceptions import ValidationError


def _error_msg(validation_error):
    errors = defaultdict(list)
    try:
        for attribute, messages in validation_error.message_dict.items():
            for message in messages:
                errors[attribute].append(message)
    except AttributeError:
        errors["__all__"] = [*validation_error.messages]

    return errors


class DesignImplementationError(Exception):
    """Exception to be raised when a design fails implementation."""

    def __init__(self, message, model=None):
        """Constructor to populate exception with message and model and class names."""
        if model is None:
            super().__init__(message)
        elif isclass(model):
            super().__init__(f"{message} for {model.__name__}")
        else:
            super().__init__(f"{message} for {model.__class__.__name__} {model}")


class DesignValidationError(Exception):
    """Exception to be raised before a design is implemented if it fails any validation checks."""

    def __str__(self) -> str:
        """The string representation of an object of the DesignValidationError class.

        Provides information about what caused the validation to fail.
        """
        msg = [f"{super().__str__()}"]
        if isinstance(self.__cause__, ValidationError):
            fields = _error_msg(self.__cause__)
            keys = list(fields.keys())
            keys.sort()
            for message in fields.pop("__all__", []):
                msg.append(f"{message}")

            for key in keys:
                if key == "__all__":
                    continue

                field_msg = "\n".join(fields[key])
                msg.append(f"**{key}:** {field_msg}")
        return "\n\n".join(msg)
