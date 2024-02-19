"""Test DesignInstance."""

from unittest import mock
import uuid
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType

from nautobot.extras.models import Status, JobResult, Job

from nautobot_design_builder.util import nautobot_version

from .test_model_design import BaseDesignTest
from .. import models, choices


class BaseDesignInstanceTest(BaseDesignTest):
    """Base fixtures for tests using design instances."""

    @staticmethod
    def create_design_instance(design_name, design):
        """Generate a DesignInstance."""
        content_type = ContentType.objects.get_for_model(models.DesignInstance)
        design_instance = models.DesignInstance(
            design=design,
            name=design_name,
            status=Status.objects.get(content_types=content_type, name=choices.DesignInstanceStatusChoices.ACTIVE),
            live_state=Status.objects.get(
                content_types=content_type, name=choices.DesignInstanceLiveStateChoices.PENDING
            ),
        )
        design_instance.validated_save()
        return design_instance

    def create_journal(self, job, design_instance, kwargs):
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
        journal = models.Journal(design_instance=design_instance, job_result=job_result)
        journal.validated_save()
        return journal

    def setUp(self):
        super().setUp()
        self.design_name = "My Design"
        self.design_instance = self.create_design_instance(self.design_name, self.design1)


class TestDesignInstance(BaseDesignInstanceTest):
    """Test DesignInstance."""

    def test_design_instance_queryset(self):
        design = models.DesignInstance.objects.get_by_natural_key(self.job1.name, self.design_name)
        self.assertIsNotNone(design)
        self.assertEqual("Simple Design - My Design", str(design))

    def test_design_cannot_be_changed(self):
        with self.assertRaises(ValidationError):
            self.design_instance.design = self.design2
            self.design_instance.validated_save()

        with self.assertRaises(ValidationError):
            self.design_instance.design = None
            self.design_instance.validated_save()

    def test_uniqueness(self):
        with self.assertRaises(IntegrityError):
            models.DesignInstance.objects.create(design=self.design1, name=self.design_name)

    def test_decommission_single_journal(self):
        """TODO"""

    def test_decommission_multiple_journal(self):
        """TODO"""
