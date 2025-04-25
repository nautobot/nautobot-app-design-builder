"""Test Design."""

from nautobot.apps.testing import ModelTestCases

from nautobot_design_builder import models
from nautobot_design_builder.tests import fixtures


class TestDesign(ModelTestCases.BaseModelTestCase):
    """Test Design."""

    model = models.Design

    @classmethod
    def setUpTestData(cls):
        """Create test data for Design Model."""
        super().setUpTestData()
        # Create 3 objects for the model test cases.
        fixtures.create_design()

    def test_create_design_only_required(self):
        """Create with only required fields, and validate null description and __str__."""
        design = models.Design.objects.create(name="Development")
        self.assertEqual(design.name, "Development")
        self.assertEqual(design.description, "")
        self.assertEqual(str(design), "Development")

    def test_create_design_all_fields_success(self):
        """Create Design with all fields."""
        design = models.Design.objects.create(name="Development", description="Development Test")
        self.assertEqual(design.name, "Development")
        self.assertEqual(design.description, "Development Test")
