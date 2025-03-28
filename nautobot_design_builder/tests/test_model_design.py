"""Test Design."""

from django.test import TestCase

from nautobot_design_builder import models


class TestDesign(TestCase):
    """Test Design."""

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
