from nautobot.utilities.testing import ViewTestCases

from nautobot_design_builder.models import Design, DesignInstance, Journal, JournalEntry
from nautobot_design_builder.tests.util import create_test_view_data


class DesignTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = Design

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()


class DesignInstanceTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = DesignInstance

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()


class JournalTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = Journal

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()


class JournalEntryTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
):
    model = JournalEntry

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()
