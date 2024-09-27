"""Test object creator methods."""

import importlib
import os
from unittest.mock import Mock, patch
import yaml

from django.db.models import Manager, Q
from django.test import TestCase

from nautobot.dcim.models import Cable

from nautobot_design_builder.design import Environment


class BuilderChecks:
    """Collection of static methods for testing designs."""

    @staticmethod
    def check_connected(test, check, index):
        """Check if two endpoints are connected with a cable."""
        value0 = _get_value(check[0])[0]
        value1 = _get_value(check[1])[0]
        cables = Cable.objects.filter(
            Q(termination_a_id=value0.id, termination_b_id=value1.id)
            | Q(termination_a_id=value1.id, termination_b_id=value0.id)
        )
        test.assertEqual(1, cables.count(), msg=f"Check {index}")

    @staticmethod
    def check_count(test, check, index):
        """Check the number of items in a collection."""
        values = _get_value(check)
        test.assertEqual(check["count"], len(values), msg=f"Check {index}")

    @staticmethod
    def check_equal(test, check, index):
        """Check that two values are equal."""
        value0 = _get_value(check[0])
        value1 = _get_value(check[1])
        if len(value0) == 1 and len(value1) == 1:
            test.assertEqual(value0[0], value1[0], msg=f"Check {index}")

        # TODO: Mysql tests fail due to unordered lists
        if isinstance(value0, list) and isinstance(value1, list):
            test.assertEqual(len(value0), len(value1))
            for item0 in value0:
                test.assertIn(item0, value1)
        else:
            test.assertEqual(value0, value1, msg=f"Check {index}")

    @staticmethod
    def check_count_equal(test, check, index):
        """Check that two values are equal."""
        value0 = _get_value(check[0])
        value1 = _get_value(check[1])
        if len(value0) == 1 and len(value1) == 1:
            test.assertEqual(value0[0], value1[0], msg=f"Check {index}")
        test.assertCountEqual(value0, value1, msg=f"Check {index}")

    @staticmethod
    def check_model_exists(test, check, index):
        """Check that a model exists."""
        values = _get_value(check)
        test.assertEqual(len(values), 1, msg=f"Check {index}")

    @staticmethod
    def check_model_not_exist(test, check, index):
        """Check that a model does not exist."""
        values = _get_value(check)
        test.assertEqual(len(values), 0, msg=f"Check {index}")


class attrgetter:  # pylint:disable=invalid-name,too-few-public-methods
    """Return a callable object that fetches attr or key from its operand.

    The attribute names can also contain dots
    """

    def __init__(self, attr):
        if not isinstance(attr, str):
            raise TypeError("attribute name must be a string")
        self._attrs = (attr,)
        names = attr.split(".")

        def func(obj):
            for name in names:
                if hasattr(obj, name):
                    obj = getattr(obj, name)
                elif name in obj:
                    obj = obj[name]
                else:
                    raise AttributeError(f"'{type(obj).__name__}' has no attribute or item '{name}'")
            return obj

        self._call = func

    def __call__(self, obj):
        return self._call(obj)


def _get_value(check_info):
    if "value" in check_info:
        value = check_info["value"]
        if isinstance(value, list):
            return value
        return [check_info["value"]]
    if "model" in check_info:
        model_class = _load_class(check_info["model"])
        queryset = model_class.objects.filter(**check_info.get("query", {}))
        if len(queryset) == 0:
            return []
        value = []
        for model in queryset:
            if "attribute" in check_info:
                model = attrgetter(check_info["attribute"])(model)
                if isinstance(model, Manager):
                    value.extend(model.all())
                elif callable(model):
                    value.append(model())
                else:
                    value.append(model)
            else:
                value.append(model)
        return value
    raise ValueError(f"Can't get value for {check_info}")


def _load_class(class_path):
    module_name, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def _testcases(data_dir):
    for filename in os.listdir(data_dir):
        if filename.endswith(".yaml"):
            with open(os.path.join(data_dir, filename), encoding="utf-8") as file:
                yield yaml.safe_load(file), filename


def builder_test_case(data_dir):
    """Decorator to load tests into a TestCase from a data directory."""

    def class_wrapper(test_class):
        for testcase, filename in _testcases(data_dir):
            # Strip the .yaml extension
            testcase_name = f"test_{filename[:-5]}"

            # Create a new closure for testcase
            def test_wrapper(testcase):
                @patch("nautobot_design_builder.design.Environment.roll_back")
                def test_runner(self, roll_back: Mock):
                    if testcase.get("skip", False):
                        self.skipTest("Skipping due to testcase skip=true")
                    extensions = []
                    for extension in testcase.get("extensions", []):
                        extensions.append(_load_class(extension))

                    with self.captureOnCommitCallbacks(execute=True):
                        for design in testcase["designs"]:
                            environment = Environment(extensions=extensions)
                            commit = design.pop("commit", True)
                            environment.implement_design(design=design, commit=commit)
                            if not commit:
                                roll_back.assert_called()

                    for index, check in enumerate(testcase.get("checks", [])):
                        for check_name, args in check.items():
                            _check_name = f"check_{check_name}"
                            if hasattr(BuilderChecks, _check_name):
                                getattr(BuilderChecks, _check_name)(self, args, index)
                            else:
                                raise ValueError(f"Unknown check {check_name} {check}")

                return test_runner

            setattr(test_class, testcase_name, test_wrapper(testcase))
        return test_class

    return class_wrapper


@builder_test_case(os.path.join(os.path.dirname(__file__), "testdata"))
class TestGeneralDesigns(TestCase):
    """Designs that should work with all Nautobot Version 1."""
