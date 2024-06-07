"API tests."
import unittest

from nautobot.utilities.testing import APIViewTestCases

from nautobot_design_builder.models import Design, Deployment, ChangeSet, ChangeRecord
from nautobot_design_builder.tests.util import create_test_view_data

# pylint: disable=missing-class-docstring


class TestDesign(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.NotesURLViewTestCase,
):
    model = Design
    brief_fields = ["display", "id", "name", "url"]

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()


class TestDeployment(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.NotesURLViewTestCase,
):
    model = Deployment
    brief_fields = ["display", "id", "name", "url"]

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()


class TestChangeSetAPI(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.NotesURLViewTestCase,
):
    model = ChangeSet
    brief_fields = ["display", "id", "url"]

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()


class TestChangeRecordAPI(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.NotesURLViewTestCase,
):
    model = ChangeRecord
    brief_fields = None

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()

    @unittest.skip
    def test_list_objects_brief(self):
        """Brief is not supported for change records."""
