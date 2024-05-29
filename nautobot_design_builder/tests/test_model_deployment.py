"""Test Deployment."""

from unittest import mock
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType

from nautobot.extras.models import Status, JobResult

from .test_model_design import BaseDesignTest
from .. import models, choices


class BaseDeploymentTest(BaseDesignTest):
    """Base fixtures for tests using design deployments."""

    @staticmethod
    def create_deployment(design_name, design):
        """Generate a Deployment."""
        content_type = ContentType.objects.get_for_model(models.Deployment)
        design_instance = models.Deployment(
            design=design,
            name=design_name,
            status=Status.objects.get(content_types=content_type, name=choices.DeploymentStatusChoices.ACTIVE),
            version=design.version,
        )
        design_instance.validated_save()
        return design_instance

    def create_change_set(self, job, design_instance, kwargs):
        """Creates a ChangeSet."""
        job_result = JobResult.objects.create(
            name=job.name,
            job_model=job,
        )
        job_result.log = mock.Mock()
        job_result.task_kwargs = kwargs
        change_set = models.ChangeSet(design_instance=design_instance, job_result=job_result)
        change_set.validated_save()
        return change_set

    def setUp(self):
        super().setUp()
        self.design_name = "My Design"
        self.design_instance = self.create_deployment(self.design_name, self.designs[0])


class TestDeployment(BaseDeploymentTest):
    """Test Deployment."""

    def test_design_instance_queryset(self):
        design = models.Deployment.objects.get_by_natural_key(self.jobs[0].name, self.design_name)
        self.assertIsNotNone(design)
        self.assertEqual(f"{self.jobs[0].job_class.Meta.name} - {self.design_name}", str(design))

    def test_design_cannot_be_changed(self):
        with self.assertRaises(ValidationError):
            self.design_instance.design = self.designs[1]
            self.design_instance.validated_save()

        with self.assertRaises(ValidationError):
            self.design_instance.design = None
            self.design_instance.validated_save()

    def test_uniqueness(self):
        with self.assertRaises(IntegrityError):
            models.Deployment.objects.create(design=self.designs[0], name=self.design_name)

    def test_decommission_single_change_set(self):
        """TODO"""

    def test_decommission_multiple_change_set(self):
        """TODO"""
