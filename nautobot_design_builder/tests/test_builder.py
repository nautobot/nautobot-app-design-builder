"""Test object creator methods."""
import importlib
from operator import attrgetter
import os
from unittest.mock import Mock, patch
import yaml

from django.db.models import Manager, Q
from django.test import TestCase

from nautobot.dcim.models import Cable

from nautobot_design_builder.design import Builder
from nautobot_design_builder.util import nautobot_version

class BuilderChecks:
  @staticmethod
  def check_connected(self, check, index):
      value0 = _get_value(check[0])[0]
      value1 = _get_value(check[1])[0]
      cables = Cable.objects.filter(
          Q(termination_a_id=value0.id, termination_b_id=value1.id)
          | Q(termination_a_id=value1.id, termination_b_id=value0.id)
      )
      self.assertEqual(1, cables.count(), msg=f"Check {index}")

  @staticmethod
  def check_count(self, check, index):
      values = _get_value(check)
      self.assertEqual(check["count"], len(values), msg=f"Check {index}")

  @staticmethod
  def check_equal(self, check, index):
      value0 = _get_value(check[0])
      value1 = _get_value(check[1])
      if len(value0) == 1 and len(value1) == 1:
          self.assertEqual(value0[0], value1[0], msg=f"Check {index}")
      self.assertEqual(value0, value1, msg=f"Check {index}")

  @staticmethod
  def check_model_exists(self, check, index):
      values = _get_value(check)
      self.assertEqual(len(values), 1, msg=f"Check {index}")

  @staticmethod
  def check_model_not_exist(self, check, index):
      values = _get_value(check)
      self.assertEqual(len(values), 0, msg=f"Check {index}")

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
            with open(os.path.join(data_dir, filename)) as file:
                yield yaml.safe_load(file), filename

def builder_test_case(data_dir):
    def class_wrapper(test_class):
        for testcase, filename in _testcases(data_dir):
            # Strip the .yaml extension
            testcase_name = f"test_{filename[:-5]}"

            @patch("nautobot_design_builder.design.Builder.roll_back")
            def test_runner(self, roll_back: Mock):
                extensions = []
                for extension in testcase.get("extensions", []):
                    extensions.append(_load_class(extension))

                for design in testcase["designs"]:
                    builder = Builder(extensions=extensions)
                    commit = design.pop("commit", True)
                    builder.implement_design(design=design, commit=commit)
                    if not commit:
                        roll_back.assert_called()

                for index, check in enumerate(testcase.get("checks", [])):
                    for check_name, args in check.items():
                        _check_name = f"check_{check_name}"
                        if hasattr(BuilderChecks, _check_name):
                          getattr(BuilderChecks, _check_name)(self, args, index)
                        else:
                          raise ValueError(f"Unknown check {check_name} {check}")
            setattr(test_class, testcase_name, test_runner)
        return test_class
    return class_wrapper

# class TestDesigns(TestCase):
    # @staticmethod
    # def _testcases():
    #     testdata = os.path.join(os.path.dirname(__file__), "testdata")
    #     for filename in os.listdir(testdata):
    #         if filename.endswith(".yaml"):
    #             with open(os.path.join(testdata, filename)) as file:
    #                 yield yaml.safe_load(file), filename

    # @staticmethod
    # def _load_class(class_path):
    #       module_name, class_name = class_path.rsplit(".", 1)
    #       module = importlib.import_module(module_name)
    #       return getattr(module, class_name)

    # @staticmethod
    # def _get_value(check_info):
    #     if "value" in check_info:
    #         value = check_info["value"]
    #         if isinstance(value, list):
    #             return value
    #         return [check_info["value"]]
    #     if "model" in check_info:
    #       model_class = TestDesigns._load_class(check_info["model"])
    #       queryset = model_class.objects.filter(**check_info.get("query", {}))
    #       if len(queryset) == 0:
    #           return []
    #       value = []
    #       for model in queryset:
    #         if "attribute" in check_info:
    #             model = attrgetter(check_info["attribute"])(model)
    #             if isinstance(model, Manager):
    #                 value.extend(model.all())
    #             elif callable(model):
    #                 value.append(model())
    #             else:
    #                 value.append(model)
    #         else:
    #           value.append(model)
    #       return value
    #     raise ValueError(f"Can't get value for {check_info}")
  
    # def _check_connected(self, check, index):
    #     value0 = self._get_value(check[0])[0]
    #     value1 = self._get_value(check[1])[0]
    #     cables = Cable.objects.filter(
    #         Q(termination_a_id=value0.id, termination_b_id=value1.id)
    #         | Q(termination_a_id=value1.id, termination_b_id=value0.id)
    #     )
    #     self.assertEqual(1, cables.count(), msg=f"Check {index}")
  
    # def _check_count(self, check, index):
    #     values = self._get_value(check)
    #     self.assertEqual(check["count"], len(values), msg=f"Check {index}")

    # def _check_equal(self, check, index):
    #     value0 = self._get_value(check[0])
    #     value1 = self._get_value(check[1])
    #     if len(value0) == 1 and len(value1) == 1:
    #         self.assertEqual(value0[0], value1[0], msg=f"Check {index}")
    #     self.assertEqual(value0, value1, msg=f"Check {index}")

    # def _check_model_exists(self, check, index):
    #     values = self._get_value(check)
    #     self.assertEqual(len(values), 1, msg=f"Check {index}")

    # def _check_model_not_exist(self, check, index):
    #     values = self._get_value(check)
    #     self.assertEqual(len(values), 0, msg=f"Check {index}")

    # @patch("nautobot_design_builder.design.Builder.roll_back")
    # def test_designs(self, roll_back: Mock):
    #     for testcase, filename in self._testcases():
    #         testcase_name = testcase.get("name", filename[:-5])
    #         with self.subTest(testcase_name), transaction.atomic():
    #             outer_sid = transaction.savepoint()
    #             extensions = []
    #             for extension in testcase.get("extensions", []):
    #                 extensions.append(self._load_class(extension))

    #             for design in testcase["designs"]:
    #                 inner_sid = transaction.savepoint()
    #                 builder = Builder(extensions=extensions)
    #                 commit = design.pop("commit", True)
    #                 builder.implement_design(design=design, commit=commit)
    #                 if not commit:
    #                     roll_back.assert_called()
    #                     transaction.savepoint_rollback(inner_sid)

    #             for index, check in enumerate(testcase.get("checks", [])):
    #                 for check_name, args in check.items():
    #                     _check_name = f"_check_{check_name}"
    #                     if hasattr(self, _check_name):
    #                       getattr(self, _check_name)(args, index)
    #                     else:
    #                       raise ValueError(f"Unknown check {check_name} {check}")
    #             transaction.savepoint_rollback(outer_sid)


@builder_test_case(os.path.join(os.path.dirname(__file__), "testdata"))
class TestGeneralDesigns(TestCase):  # pylint:disable=too-many-public-methods
    """Designs that should work with all versions of Nautobot."""


@builder_test_case(os.path.join(os.path.dirname(__file__), "testdata", "nautobot_v1"))
class TestV1Designs(TestCase):  # pylint:disable=too-many-public-methods
    """Designs that only work in Nautobot 1.x"""
    # builder = None

    def setUp(self):
        if nautobot_version >= "2.0.0":
            self.skipTest("These tests are only supported in Nautobot 1.x")
        super().setUp()

    # def implement_design(self, design_input, commit=True):
    #     """Convenience function for implementing a design."""
    #     self.builder = Builder()
    #     self.builder.implement_design(design=yaml.safe_load(design_input), commit=commit)

    # def test_create_or_update_rack(self):
    #     design = """
    #     manufacturers:
    #     - name: "Vendor"
    #     device_types:
    #     - "!create_or_update:model": "test model"
    #       "!create_or_update:manufacturer__name": "Vendor"
    #     device_roles:
    #     - "name": "role"
    #     sites:
    #     - "name": "Site"
    #       "status__name": "Active"
    #     devices:
    #     - "!create_or_update:name": "test device"
    #       "!create_or_update:device_type__manufacturer__name": "Vendor"
    #       "device_role__name": "role"
    #       "site__name": "Site"
    #       "status__name": "Active"
    #       "rack":
    #         "!create_or_update:name": "rack-1"
    #         "!create_or_update:site__name": "Site"
    #         "status__name": "Active"
    #     """
    #     self.implement_design(design)
    #     device = Device.objects.get(name="test device")
    #     self.assertEqual("rack-1", device.rack.name)
