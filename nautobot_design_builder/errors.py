"""Module containing error Exception classes specific to Design Builder."""
from collections import defaultdict
from inspect import isclass

from django.core.exceptions import ValidationError
from django.db.models import Model


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


class DesignModelError(Exception):
    """Parent class for all model related design errors."""

    def __init__(self, model=None, parent=None) -> None:
        """Initialize a DesignError with optional model_stack.

        Args:
            model: The model that generated the error.
            parent: If model is a django model (as opposed to a design
            builder ModelInstance) then a parent can be specified
            in order to better represent the relationship of the
            model within the design.
        """
        super().__init__()
        self.model = model
        self.parent = parent

    @staticmethod
    def _model_str(model):
        instance_str = None
        if not isinstance(model, Model) and not hasattr(model, "instance"):
            if isclass(model):
                return model.__name__
            try:
                return str(model)
            except Exception:  # pylint: disable=broad-exception-caught
                # Sometimes when converting a model to a string the __str__
                # method itself produces an exceptions, like when an attribute
                # hasn't been set or something. Whatever it is commonly is
                # the cause of the original exception, we don't want to
                # cause *another* exception because of that.
                return model.__class__.__name__

        model_class = model.__class__
        # if it looks like a duck...
        if hasattr(model, "instance"):
            model_class = model.model_class
            model = model.instance

        if model:
            try:
                instance_str = str(model)
            except Exception:  # pylint: disable=broad-exception-caught
                # Sometimes when converting a model to a string the __str__
                # method itself produces an exceptions, like when an attribute
                # hasn't been set or something. Whatever it is commonly is
                # the cause of the original exception, we don't want to
                # cause *another* exception because of that.
                instance_str = model.__class__.__name__
        model_str = model_class._meta.verbose_name.capitalize()
        if instance_str:
            model_str = f"{model_str} {instance_str}"
        return model_str

    @staticmethod
    def _object_to_markdown(obj, indentation=""):
        msg = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                msg.append(f"{indentation}- **{key}:** ")
                if isinstance(value, dict):
                    msg.append(DesignModelError._object_to_markdown(value, indentation=f"{indentation}    "))
                else:
                    msg[-1] += DesignModelError._model_str(value)
        else:
            msg.append(f"{indentation}- {DesignModelError._model_str(obj)}")
        return "\n".join(msg)

    @property
    def model_str(self):
        """User-friendly name for the model instance."""
        return DesignModelError._model_str(self.model)

    @property
    def path_str(self):
        """List of properly indented parents for the model."""
        path_msg = []
        model = self.model
        while model is not None:
            path_msg.insert(0, DesignModelError._model_str(model))
            if not isclass(model) and hasattr(model, "parent"):
                model = model.parent
            elif self.parent:
                model = self.parent
                self.parent = None
            else:
                model = None
        # don't include the top level model in the ancestry
        # tree because details about it should be included
        # in the implementing class's __str__ method
        path_msg.pop()
        indentation = ""

        for i, msg in enumerate(path_msg):
            path_msg[i] = f"{indentation}- {msg}"
            indentation += "    "

        return indentation, "\n".join(path_msg)


class DesignValidationError(DesignModelError):
    """Exception indicating a design failed validation checks.

    A DesignValidationError can be raised by `validate_` methods
    in a `Context` or by the `Builder` during implementation.
    During the implementation process, if any object fails validation
    during it's `full_clean` check, then the ValidationError is raised
    from that point as a DesignValidationError.
    """

    def __str__(self) -> str:
        """The string representation of an object of the DesignValidationError class.

        Provides information about what caused the validation to fail.
        """
        msg = []
        indentation, path_msg = self.path_str
        if path_msg:
            msg.append(path_msg)
        msg.append(f"{indentation}{self.model_str} failed validation")
        if isinstance(self.__cause__, ValidationError):
            fields = _error_msg(self.__cause__)
            keys = list(fields.keys())
            keys.sort()
            for message in fields.pop("__all__", []):
                msg.append(f"{indentation}  {message}")

            for key in keys:
                if key == "__all__":
                    continue

                field_msg = "\n".join(fields[key])
                msg.append(f"{indentation}  **{key}:** {field_msg}")
        return "\n\n".join(msg)


class DesignQueryError(DesignModelError):
    """Exception indicating design builder could not find the object."""

    def __init__(self, model=None, query_filter=None, **kwargs):
        """Initialize a design query error.

        Args:
            model: Model or model class this query error corresponds to.
            query_filter: Query filter the generated the error.
        """
        super().__init__(model=model, **kwargs)
        self.query_filter = query_filter

    def __str__(self) -> str:
        """The string representation of an object of the DoesNotExistError class."""
        msg = []
        indentation, path_msg = self.path_str
        if path_msg:
            msg.append(path_msg)
        msg.append(f"{indentation}- {self.model_str}:")
        if hasattr(self.model, "query_filter"):
            msg.append(DesignModelError._object_to_markdown(self.model.query_filter, indentation=f"{indentation}    "))
        elif self.query_filter:
            msg.append(DesignModelError._object_to_markdown(self.query_filter, indentation=f"{indentation}    "))
        else:
            msg.append(DesignModelError._object_to_markdown(self.model.filter, indentation=f"{indentation}    "))
        return "\n".join(msg)


class DoesNotExistError(DesignQueryError):
    """Raised when a `ModelInstance` underlying database object cannot be found."""

    def __str__(self):
        """Error message with context."""
        return f"Failed to find {self.model_str} matching query.\n\n{super().__str__()}"


class MultipleObjectsReturnedError(DesignQueryError):
    """Raised when a `ModelInstance` query matches more than one database object."""

    def __str__(self):
        """Error message with context."""
        return f"Multiple {self.model_str} objects matched query.\n\n{super().__str__()}"
