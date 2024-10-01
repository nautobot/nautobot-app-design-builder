"""Utilities for debugging object assignment and saving."""

from django.db import models

indent = ""  # pylint:disable=invalid-name
DEBUG = False


class ObjDetails:  # noqa:D101  # pylint:disable=too-few-public-methods,missing-class-docstring
    def __init__(self, obj):  # noqa:D107  # pylint:disable=missing-function-docstring
        self.design_instance = obj
        if hasattr(obj, "design_instance"):
            self.design_instance = obj.design_instance
        try:
            description = str(obj)
            if description.startswith("<class"):
                description = None
        except Exception:  # pylint:disable=broad-exception-caught
            description = None

        self.obj = obj
        self.obj_class = obj.__class__.__name__
        self.obj_id = str(getattr(self.design_instance, "id", None))
        if hasattr(self.design_instance, "name"):
            self.name = getattr(self.design_instance, "name")
        else:
            self.name = None
        self.description = description

    def __str__(self):  # noqa:D105  # pylint:disable=missing-function-docstring
        if isinstance(self.design_instance, models.Model):
            string = self.obj_class + " "
            if self.name is not None:
                string += '"' + self.name + '"' + ":"
            elif self.description:
                string += self.description + ":"
            string += self.obj_id
            return string
        if isinstance(self.design_instance, dict):
            return str(self.obj)
        return self.description or self.name or self.obj_class


def debug(*args, **kwargs):  # noqa:D103  # pylint:disable=missing-function-docstring
    print(indent, *args, **kwargs)


def debug_set(wrapped):  # noqa:D103  # pylint:disable=missing-function-docstring
    def wrapper(self, obj, value, *args, **kwargs):
        obj_details = ObjDetails(obj)
        value_details = ObjDetails(value)
        global indent  # pylint:disable=global-statement
        debug(self.__class__.__name__, "setting", self.field_name, "on", obj_details, "to", value_details)
        indent += "  "
        wrapped(self, obj, value, *args, **kwargs)
        indent = indent[0:-2]
        debug("Exit", self.__class__.__name__)

    if DEBUG:
        return wrapper
    return wrapped
