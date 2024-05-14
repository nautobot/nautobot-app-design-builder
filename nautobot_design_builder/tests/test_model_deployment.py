"""Test Deployment."""

from unittest import mock
import uuid
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType

from nautobot.extras.models import Status, JobResult, Job

from nautobot_design_builder.util import nautobot_version

from .test_model_design import BaseDesignTest
from .. import models, choices


class BaseDeploymentTest(BaseDesignTest):
    """Base fixtures for tests using design instances."""

    @staticmethod
    def create_deployment(design_name, design):
        """Generate a Deployment."""
        content_type = ContentType.objects.get_for_model(models.Deployment)
        deployment = models.Deployment(
            design=design,
            name=design_name,
            status=Status.objects.get(content_types=content_type, name=choices.DeploymentStatusChoices.ACTIVE),
            version=design.version,
        )
        deployment.validated_save()
        return deployment

    def create_journal(self, job, deployment, kwargs):
        """Creates a Journal."""
        job_result = JobResult(
            job_model=self.job1,
            name=job.class_path,
            job_id=uuid.uuid4(),
            obj_type=ContentType.objects.get_for_model(Job),
        )
        job_result.log = mock.Mock()
        if nautobot_version < "2.0":
            job_result.job_kwargs = {"data": kwargs}
        else:
            job_result.task_kwargs = kwargs
        job_result.validated_save()
        journal = models.Journal(deployment=deployment, job_result=job_result)
        journal.validated_save()
        return journal

    def setUp(self):
        super().setUp()
        self.design_name = "My Design"
        self.deployment = self.create_deployment(self.design_name, self.design1)


class TestDeployment(BaseDeploymentTest):
    """Test Deployment."""

    def test_deployment_queryset(self):
        design = models.Deployment.objects.get_by_natural_key(self.job1.name, self.design_name)
        self.assertIsNotNone(design)
        self.assertEqual("Simple Design - My Design", str(design))

    def test_design_cannot_be_changed(self):
        with self.assertRaises(ValidationError):
            self.deployment.design = self.design2
            self.deployment.validated_save()

        with self.assertRaises(ValidationError):
            self.deployment.design = None
            self.deployment.validated_save()

    def test_uniqueness(self):
        with self.assertRaises(IntegrityError):
            models.Deployment.objects.create(design=self.design1, name=self.design_name)

    def test_decommission_single_journal(self):
        """TODO"""

    def test_decommission_multiple_journal(self):
        """TODO"""
