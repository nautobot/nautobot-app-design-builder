"""Module containing error Exception classes specific to Design Builder."""
from inspect import isclass

from django.core.exceptions import ValidationError


def _error_msg(err, messages=None):
    if messages is None:
        messages = {}
    messages.setdefault("__all__", [])
    if hasattr(err, "error_dict"):
        for field, errors in err.error_dict.items():
            messages.setdefault(field, [])
            for err1 in errors:
                messages[field].extend(_error_msg(err1)["__all__"])
    elif hasattr(err, "message"):
        if isinstance(err.message, ValidationError):
            _error_msg(err.message, messages)
        else:
            messages["__all__"].append(err.message)
    elif hasattr(err, "error_list"):
        for err1 in err.error_list:
            _error_msg(err1, messages)
    else:
        messages["__all__"].append(str(err))

    return messages


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
        msg = f"{super().__str__()}"
        if isinstance(self.__cause__, ValidationError):
            fields = _error_msg(self.__cause__)
            keys = list(fields.keys())
            keys.sort()
            for message in fields.pop("__all__", []):
                msg += f"\n\n{message}"

            for key in keys:
                if key == "__all__":
                    continue
                msg += "\n\n**%s:** %s" % (key, "\n\n".join(fields[key]))

        return msg
