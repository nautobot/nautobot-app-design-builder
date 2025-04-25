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

        self.assertEqual(self.designs[0].job_id, self.jobs[0].id)
        self.assertEqual(self.designs[1].job_id, self.jobs[1].id)
        self.assertEqual(str(self.designs[0]), self.designs[0].name)

    def test_design_queryset(self):
        self.assertIsNotNone(self.designs[0])
        self.assertEqual(self.designs[0].job_id, self.jobs[0].id)

    def test_job_cannot_be_changed(self):
        with self.assertRaises(ValidationError):
            self.designs[0].job = self.jobs[1]
            self.designs[0].validated_save()

        with self.assertRaises(ValidationError):
            self.designs[0].job = None
            self.designs[0].validated_save()

    def test_no_duplicates(self):
        with self.assertRaises(IntegrityError):
            models.Design.objects.create(job=self.jobs[0])
