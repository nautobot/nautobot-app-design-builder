"""Test Views."""

from nautobot.utilities.testing import ViewTestCases

from nautobot_design_builder.models import Design, DesignInstance, Journal, JournalEntry
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


class TestCaseDesignInstance(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = DesignInstance

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()


class TestCaseJournal(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = Journal

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()


class TestCaseJournalEntry(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
):
    model = JournalEntry

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()
