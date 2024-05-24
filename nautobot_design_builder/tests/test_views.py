"""Test Views."""

from nautobot.utilities.testing import ViewTestCases

from nautobot_design_builder.models import Design, Deployment, ChangeSet, ChangeRecord
from nautobot_design_builder.tests.util import create_test_view_data

# pylint: disable=missing-class-docstring


class TestCaseDesign(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = Design

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()


class TestCaseDeployment(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = Deployment

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()


class TestCaseChangeSet(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = ChangeSet

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()


class TestCaseChangeRecord(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
):
    model = ChangeRecord

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()
