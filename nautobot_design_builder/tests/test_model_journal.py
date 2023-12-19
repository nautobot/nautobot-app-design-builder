"""Test Journal."""

from typing import Type
from unittest import mock
import uuid

from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Manufacturer
from nautobot.extras.models import JobResult, Job
from nautobot_design_builder.design_job import DesignJob

from nautobot_design_builder.util import nautobot_version

from .test_model_design_instance import BaseDesignInstanceTest
from .. import models


class BaseJournalTest(BaseDesignInstanceTest):
    def create_journal(self, job, design_instance, kwargs):
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
        self.original_name = "original equipment manufacturer"
        self.manufacturer = Manufacturer.objects.create(name=self.original_name)
        self.job_kwargs = {
            "manufacturer": f"{self.manufacturer.pk}",
            "instance": "my instance",
        }

        self.journal = self.create_journal(self.job1, self.design_instance, self.job_kwargs)


class TestJournal(BaseJournalTest):
    """Test Journal."""

    def test_user_input(self):
        user_input = self.journal.user_input
        self.assertEqual(self.manufacturer, user_input["manufacturer"])
        self.assertEqual("my instance", user_input["instance"])
