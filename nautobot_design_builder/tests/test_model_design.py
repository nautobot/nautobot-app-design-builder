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
        self.jobs = []
        self.designs = []
        for cls in [test_designs.SimpleDesign, test_designs.SimpleDesignReport]:
            job = JobModel.objects.get(name=cls.Meta.name)
            self.jobs.append(job)
            self.designs.append(models.Design.objects.get(job=job))


class TestDesign(BaseDesignTest):
    """Test Design."""

    def test_create_from_signal(self):
        # TODO: move back to 2 when the designs are outside of the repo

        self.assertEqual(
            [job.name for job in JobModel.objects.filter(grouping=test_designs.name).order_by("name")],
            [design.name for design in models.Design.objects.filter(job__grouping=test_designs.name).order_by("name")],
        )
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
