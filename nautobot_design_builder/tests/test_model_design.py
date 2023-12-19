"""Test Design."""
from os import path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from nautobot.extras.models import Job as JobModel

from nautobot_design_builder.tests import DesignTestCase

from .designs import test_designs
from .. import models


class BaseDesignTest(DesignTestCase):
    """Common fixtures for design builder model testing."""

    def setUp(self):
        super().setUp()
        settings.JOBS_ROOT = path.dirname(test_designs.__file__)
        defaults = {
            "grouping": "Designs",
            "source": "local",
            "installed": True,
            "module_name": test_designs.__name__.split(".")[-1],  # pylint: disable=use-maxsplit-arg
        }

        self.job1 = JobModel(
            **defaults.copy(),
            name="Simple Design",
            job_class_name=test_designs.SimpleDesign.__name__,
        )
        self.job1.validated_save()
        self.design1 = models.Design.objects.get(job=self.job1)

        self.job2 = JobModel(
            **defaults.copy(),
            name="Simple Design Report",
            job_class_name=test_designs.SimpleDesignReport.__name__,
        )
        self.job2.validated_save()
        self.design2 = models.Design.objects.get(job=self.job2)


class TestDesign(BaseDesignTest):
    """Test Design."""

    def test_create_from_signal(self):
        self.assertEqual(2, models.Design.objects.all().count())
        self.assertEqual(self.design1.job_id, self.job1.id)
        self.assertEqual(self.design2.job_id, self.job2.id)
        self.assertEqual(str(self.design1), self.design1.name)

    def test_design_queryset(self):
        self.assertIsNotNone(self.design1)
        self.assertEqual(self.design1.job_id, self.job1.id)

    def test_job_cannot_be_changed(self):
        with self.assertRaises(ValidationError):
            self.design1.job = self.job2
            self.design1.validated_save()

        with self.assertRaises(ValidationError):
            self.design1.job = None
            self.design1.validated_save()

    def test_no_duplicates(self):
        with self.assertRaises(IntegrityError):
            models.Design.objects.create(job=self.job1)
