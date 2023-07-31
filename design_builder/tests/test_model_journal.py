"""Test Journal."""

import uuid

from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Manufacturer
from nautobot.extras.models import JobResult, Job

from design_builder.util import nautobot_version

from .test_model_design_instance import BaseDesignInstanceTest
from .. import models


class TestJournal(BaseDesignInstanceTest):
    """Test Journal."""

    def setUp(self):
        super().setUp()
        self.manufacturer = Manufacturer.objects.create(name="manufacturer")
        kwargs = {
            "manufacturer": f"{self.manufacturer.pk}",
            "instance": "my instance",
        }

        self.job_result = JobResult(
            job_model=self.job1,
            name=self.job1.class_path,
            job_id=uuid.uuid4(),
            obj_type=ContentType.objects.get_for_model(Job),
        )
        if nautobot_version < "2.0":
            self.job_result.job_kwargs = {"data": kwargs}
        else:
            self.job_result.task_kwargs = kwargs
        self.job_result.validated_save()
        self.journal = models.Journal(design_instance=self.design_instance, job_result=self.job_result)
        self.journal.validated_save()

    def test_user_input(self):
        user_input = self.journal.user_input
        self.assertEqual(self.manufacturer, user_input["manufacturer"])
        self.assertEqual("my instance", user_input["instance"])
