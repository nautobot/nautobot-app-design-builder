"""Unit tests related to the recursive functions for reducing and updating designs."""

import copy
import unittest
import os
import json

from nautobot_design_builder.recursive import reduce_design


class TestReduce(unittest.TestCase):  # pylint: disable=missing-class-docstring
    def setUp(self):
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_reduce_design(self):  # pylint: disable=too-many-locals
        test_folders = ["test1", "test2", "test3", "test4", "test5"]
        for folder_name in test_folders:
            with self.subTest(folder_name):
                folder_path = os.path.join(os.path.dirname(__file__), "testdata_reduce")
                design_filename = os.path.join(folder_path, folder_name, "design.json")
                previous_design_filename = os.path.join(folder_path, folder_name, "previous_design.json")
                goal_design_filename = os.path.join(folder_path, folder_name, "goal_design.json")
                goal_elements_to_be_decommissioned_filename = os.path.join(
                    folder_path, folder_name, "goal_elements_to_be_decommissioned.json"
                )

        with open(design_filename, encoding="utf-8") as design_file, open(
            previous_design_filename, encoding="utf-8"
        ) as previous_design_file, open(goal_design_filename, encoding="utf-8") as goal_design_file, open(
            goal_elements_to_be_decommissioned_filename, encoding="utf-8"
        ) as goal_elements_to_be_decommissioned_file:
            design = json.load(design_file)
            previous_design = json.load(previous_design_file)
            goal_design = json.load(goal_design_file)
            goal_elements_to_be_decommissioned = json.load(goal_elements_to_be_decommissioned_file)

            elements_to_be_decommissioned = {}
            future_design = copy.deepcopy(design)
            ext_keys_to_be_simplified = []
            for key, new_value in design.items():
                old_value = previous_design[key]
                future_value = future_design[key]
                to_delete = reduce_design(new_value, old_value, future_value, elements_to_be_decommissioned, key)
                if to_delete:
                    ext_keys_to_be_simplified.append(key)

            for key, value in goal_design.items():
                self.assertEqual(value, design[key])

            for key, value in goal_elements_to_be_decommissioned.items():
                for item1, item2 in zip(value, elements_to_be_decommissioned[key]):
                    self.assertEqual(tuple(item1), item2)


if __name__ == "__main__":
    unittest.main()
