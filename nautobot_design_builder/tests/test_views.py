"""Unit tests for views."""

from nautobot.apps.testing import ViewTestCases

from nautobot_design_builder import models
from nautobot_design_builder.tests import fixtures


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
        fixtures.create_design()
