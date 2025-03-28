"""Unit tests for nautobot_design_builder."""

from nautobot.apps.testing import APIViewTestCases

from nautobot_design_builder import models
from nautobot_design_builder.tests import fixtures


class DesignAPIViewTest(APIViewTestCases.APIViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the API viewsets for Design."""

    model = models.Design
    create_data = [
        {
            "name": "Test Model 1",
            "description": "test description",
        },
        {
            "name": "Test Model 2",
        },
    ]
    bulk_update_data = {"description": "Test Bulk Update"}

    @classmethod
    def setUpTestData(cls):
        fixtures.create_design()
