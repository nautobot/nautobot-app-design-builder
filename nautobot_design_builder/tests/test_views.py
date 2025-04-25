"""Test Views."""

from nautobot.apps.testing import ViewTestCases

from nautobot_design_builder.models import ChangeRecord, ChangeSet, Deployment, Design
from nautobot_design_builder.tests.util import create_test_view_data

# pylint: disable=missing-class-docstring


class DesignViewTest(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the Design views."""

    model = models.Design
    bulk_edit_data = {"description": "Bulk edit views"}
    form_data = {
        "name": "Test 1",
        "description": "Initial model",
    }

    update_data = {
        "name": "Test 2",
        "description": "Updated model",
    }

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
