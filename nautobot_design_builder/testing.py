"""This module provides a framework for testing designs."""

import importlib
import logging
import os
import shutil
import tempfile
from typing import Type
from unittest.mock import PropertyMock, patch

import yaml
from django.db.models import Manager, Q
from django.test import TestCase
from nautobot.dcim.models import Cable
from nautobot.extras.models import Job, JobResult

from nautobot_design_builder.design import Environment
from nautobot_design_builder.design_job import DesignJob


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
    def check_equal(test, check, index):
        """Check that two values are equal."""
        value0 = _get_value(check[0])
        value1 = _get_value(check[1])

        # TODO: Mysql tests fail due to unordered lists
        if isinstance(value0, list) and isinstance(value1, list):
            test.assertEqual(len(value0), len(value1))
            for item0 in value0:
                test.assertIn(item0, value1)
        else:
            test.assertEqual(value0, value1, msg=f"Check {index}")

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


class attrgetter:  # pylint:disable=invalid-name,too-few-public-methods
    """Return a callable object that fetches attr or key from its operand.

    The attribute names can also contain dots
    """

    def __init__(self, attr):
        """Initialize the attrgetter object."""
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
        """Call the attrgetter object."""
        return self._call(obj)


def _get_value(check_info):
    if "value" in check_info:
        return check_info["value"]
    if "model" in check_info:
        model_class = _load_class(check_info["model"])
        queryset = model_class.objects.filter(**check_info.get("query", {}))
        if check_info.get("count"):
            return int(len(queryset))
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


class RunChecksMixin:  # pylint:disable=too-few-public-methods
    """Mixin for running checks on a testcase."""

    def run_checks(self, checks):
        """Run checks on a testcase."""
        for index, check in enumerate(checks):
            for check_name, args in check.items():
                _check_name = f"check_{check_name}"
                if hasattr(BuilderChecks, _check_name):
                    getattr(BuilderChecks, _check_name)(self, args, index)
                else:
                    raise ValueError(f"Unknown check {check_name} {check}")


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


class BuilderTestCase(TestCase, RunChecksMixin, metaclass=_BuilderTestCaseMeta):
    """This class provides a framework for running tests locally with defined YAML files."""

    def _run_test_case(self, testcase, data_dir):
        with patch("nautobot_design_builder.design.Environment.roll_back") as roll_back:
            self.run_checks(testcase.get("pre_checks", []))

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

            self.run_checks(testcase.get("checks", []))


class DesignTestCase(TestCase):
    """DesignTestCase aides in creating unit tests for design jobs and templates."""

    def setUp(self):
        """Setup a mock git repo to watch for config context creation."""
        super().setUp()
        self.data = {
            "deployment_name": "Test Design",
        }
        self.logged_messages = []
        self.git_patcher = patch("nautobot_design_builder.ext.GitRepo")
        self.git_mock = self.git_patcher.start()

        self.git_path = tempfile.mkdtemp()
        git_instance_mock = PropertyMock()
        git_instance_mock.return_value.path = self.git_path
        self.git_mock.side_effect = git_instance_mock

    def get_mocked_job(self, design_class: Type[DesignJob]):
        """Create an instance of design_class and properly mock request and job_result for testing."""
        job_model = Job.objects.get(module_name=design_class.__module__, job_class_name=design_class.__name__)
        job = design_class()
        job.job_result = JobResult.objects.create(
            name="Fake Job Result",
            job_model=job_model,
        )
        job.saved_files = {}

        def save_design_file(filename, content):
            job.saved_files[filename] = content

        job.save_design_file = save_design_file
        self.logged_messages = []

        class _CaptureLogHandler(logging.Handler):
            def emit(handler, record: logging.LogRecord) -> None:  # pylint:disable=no-self-argument,arguments-renamed
                message = handler.format(record)
                obj = getattr(record, "object", None)
                self.logged_messages.append(
                    {
                        "message": message,
                        "obj": obj,
                        "level_choice": record.levelname,
                        "grouping": getattr(record, "grouping", record.funcName),
                    }
                )

        job.logger.addHandler(_CaptureLogHandler())
        return job

    def assert_context_files_created(self, *filenames):
        """Confirm that the list of filenames were created as part of the design implementation."""
        for filename in filenames:
            self.assertTrue(os.path.exists(os.path.join(self.git_path, filename)), f"{filename} was not created")

    def tearDown(self):
        """Remove temporary files."""
        self.git_patcher.stop()
        shutil.rmtree(self.git_path)
        super().tearDown()


class VerifyDesignTestCase(DesignTestCase, RunChecksMixin):
    """VerifyDesignTestCase aides in verifying the test cases with queries."""

    job_design = None
    check_file = None
    job_data = {}

    def run_design_test(self):
        """This is what class's that inherit from `VerifyDesignTestCase` call to setup and run."""
        if self.job_design is None:
            raise ValueError("The class attribute `job_design` was not defined")
        if self.check_file is None:
            raise ValueError("The class attribute `check_file` was not defined")

        job = self.get_mocked_job(self.job_design)
        job.run(data=self.job_data, dryrun=False)
        with open(self.check_file, "r", encoding="utf-8") as file:
            checks_data = yaml.safe_load(file)
            checks = checks_data.get("checks", [])
            if not checks:
                raise ValueError(f"Check file {self.check_file} does not contain any checks")
        self.run_checks(checks)
