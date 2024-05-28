"""Test Design."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from nautobot.extras.models import Job as JobModel
from nautobot.extras.utils import refresh_job_model_from_job_class

from nautobot_design_builder.tests import DesignTestCase

from .designs import test_designs
from .. import models


class BaseDesignTest(DesignTestCase):
    """Common fixtures for design builder model testing."""

    def setUp(self):
        super().setUp()
        self.job, _ = refresh_job_model_from_job_class(JobModel, "plugins", test_designs.IntegrationDesign)
        self.design = models.Design.objects.get(job=self.job)
        self.job2, _ = refresh_job_model_from_job_class(JobModel, "plugins", test_designs.SimpleDesignReport)


class TestDesign(BaseDesignTest):
    """Test Design."""

    def test_create_from_signal(self):
        self.assertEqual(5, models.Design.objects.all().count())
        self.assertEqual(self.design.job_id, self.job.id)
        self.assertEqual(str(self.design), self.design.name)

    def test_design_queryset(self):
        # TODO: What is the point of this unittest?
        self.assertIsNotNone(self.design)
        self.assertEqual(self.design.job_id, self.job.id)

    def test_job_cannot_be_changed(self):
        with self.assertRaises(ValidationError):
            self.design.job = self.job2
            self.design.validated_save()

        with self.assertRaises(ValidationError):
            self.design.job = None
            self.design.validated_save()

    def test_no_duplicates(self):
        with self.assertRaises(IntegrityError):
            models.Design.objects.create(job=self.job)
