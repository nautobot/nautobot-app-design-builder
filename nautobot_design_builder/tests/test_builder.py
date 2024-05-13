"""Test object creator methods."""

import importlib
from operator import attrgetter
import os
from unittest.mock import patch
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

    @staticmethod
    def check_in(test, check, index):
        """Check that a model does not exist."""
        value0 = _get_value(check[0])[0]
        value1 = _get_value(check[1])
        if len(value1) == 1:
            value1 = value1[0]
        test.assertIn(value0, value1, msg=f"Check {index}")

    @staticmethod
    def check_not_in(test, check, index):
        """Check that a model does not exist."""
        value0 = _get_value(check[0])[0]
        value1 = _get_value(check[1])
        if len(value1) == 1:
            value1 = value1[0]
        test.assertNotIn(value0, value1, msg=f"Check {index}")


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


class _BuilderTestCaseMeta(type):
    def __new__(mcs, name, bases, dct):
        cls = super().__new__(mcs, name, bases, dct)
        data_dir = getattr(cls, "data_dir", None)
        if data_dir is None:
            return cls

        for testcase, filename in _testcases(data_dir):
            if testcase.get("abstract", False):
                continue
            # Strip the .yaml extension
            testcase_name = f"test_{filename[:-5]}"

            # Create a new closure for testcase
            def test_wrapper(testcase):
                def test_runner(self: "BuilderTestCase"):
                    if testcase.get("skip", False):
                        self.skipTest("Skipping due to testcase skip=true")
                    self._run_test_case(testcase, cls.data_dir)  # pylint:disable=protected-access

                return test_runner

            setattr(cls, testcase_name, test_wrapper(testcase))
        return cls


class BuilderTestCase(TestCase, metaclass=_BuilderTestCaseMeta):  # pylint:disable=missing-class-docstring
    def _run_checks(self, checks):
        for index, check in enumerate(checks):
            for check_name, args in check.items():
                _check_name = f"check_{check_name}"
                if hasattr(BuilderChecks, _check_name):
                    getattr(BuilderChecks, _check_name)(self, args, index)
                else:
                    raise ValueError(f"Unknown check {check_name} {check}")

    def _run_test_case(self, testcase, data_dir):
        with patch("nautobot_design_builder.design.Environment.roll_back") as roll_back:
            self._run_checks(testcase.get("pre_checks", []))

            depends_on = testcase.pop("depends_on", None)
            if depends_on:
                depends_on_path = os.path.join(data_dir, depends_on)
                depends_on_dir = os.path.dirname(depends_on_path)
                with open(depends_on_path, encoding="utf-8") as file:
                    self._run_test_case(yaml.safe_load(file), depends_on_dir)

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

            self._run_checks(testcase.get("checks", []))


class TestGeneralDesigns(BuilderTestCase):
    """Designs that should work with all versions of Nautobot."""

    data_dir = os.path.join(os.path.dirname(__file__), "testdata")
