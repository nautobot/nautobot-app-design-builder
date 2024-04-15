"""Unit tests related to the recursive functions for updating designs with UUIDs."""

import os
import json
import unittest

from nautobot_design_builder.recursive import inject_nautobot_uuids


class TestInjectUUIDs(unittest.TestCase):  # pylint: disable=missing-class-docstring
    def setUp(self):
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_inject_uuids(self):
        test_folders = ["test1", "test2"]
        for folder_name in test_folders:
            with self.subTest(f"test_reduce_design_{folder_name}"):
                folder_path = os.path.join(os.path.dirname(__file__), "testdata_inject_uuids")
                deferred_data_filename = os.path.join(folder_path, folder_name, "deferred_data.json")
                goal_data_filename = os.path.join(folder_path, folder_name, "goal_data.json")
                future_data_filename = os.path.join(folder_path, folder_name, "future_data.json")
                with open(deferred_data_filename, encoding="utf-8") as deferred_file, open(
                    goal_data_filename, encoding="utf-8"
                ) as goal_data_file, open(future_data_filename, encoding="utf-8") as future_data_file:
                    deferred_data = json.load(deferred_file)
                    future_data = json.load(future_data_file)
                    goal_data = json.load(goal_data_file)

                    inject_nautobot_uuids(deferred_data, future_data)
                    self.assertEqual(future_data, goal_data)
