"""Test Deployment."""

from unittest import mock
import uuid
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType

from nautobot.extras.models import Status, JobResult, Job

from .test_model_design import BaseDesignTest
from .. import models, choices


class BaseDeploymentTest(BaseDesignTest):
    """Base fixtures for tests using design deployments."""

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

    def create_change_set(self, job, deployment, kwargs):
        """Creates a ChangeSet."""
        job_result = JobResult(
            job_model=self.job,
            name=job.class_path,
            job_id=uuid.uuid4(),
            obj_type=ContentType.objects.get_for_model(Job),
        )
        job_result.log = mock.Mock()
        job_result.job_kwargs = {"data": kwargs}
        job_result.validated_save()
        change_set = models.ChangeSet(deployment=deployment, job_result=job_result)
        change_set.validated_save()
        return change_set

    def create_change_record(self, design_object, changes, full_control=False, active=False):
        """Generate a ChangeRecord."""
        return models.ChangeRecord(
            design_object=design_object,
            changes=changes,
            full_control=full_control,
            change_set=self.change_set,
            active=active,
            index=self.change_set._next_index(),  # pylint:disable=protected-access
        )

    def setUp(self):
        super().setUp()
        self.design_name = "My Design"
        self.deployment = self.create_deployment(self.design_name, self.design)

        self.customer_name = "Customer 1"
        self.job_kwargs = {
            "customer_name": self.customer_name,
            "deployment_name": "my instance",
        }
        self.change_set = self.create_change_set(self.job, self.deployment, self.job_kwargs)


class TestDeployment(BaseDeploymentTest):
    """Test Deployment."""

    def test_deployment_queryset(self):
        design = models.Deployment.objects.get_by_natural_key(self.job.name, self.design_name)
        self.assertIsNotNone(design)
        self.assertEqual(f"{self.design} - {self.design_name}", str(design))

    def test_design_cannot_be_changed(self):
        with self.assertRaises(ValidationError):
            self.deployment.design = None
            self.deployment.validated_save()

    def test_uniqueness(self):
        with self.assertRaises(IntegrityError):
            models.Deployment.objects.create(design=self.design, name=self.design_name)

    def test_decommission_single_change_set(self):
        """TODO"""

    def test_decommission_multiple_change_set(self):
        """TODO"""
