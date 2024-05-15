"""Unit tests for nautobot_design_builder plugin."""

import shutil
import tempfile
from os import path
from typing import Type
from unittest import mock
from unittest.mock import PropertyMock, patch
import uuid

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from nautobot.extras.utils import refresh_job_model_from_job_class
from nautobot.extras.models import Job, JobResult
from nautobot_design_builder.design_job import DesignJob


class DesignTestCase(TestCase):
    """DesignTestCase aides in creating unit tests for design jobs and templates."""

    def setUp(self):
        """Setup a mock git repo to watch for config context creation."""
        super().setUp()
        self.data = {}
        self.logged_messages = []
        self.git_patcher = patch("nautobot_design_builder.ext.GitRepo")
        self.git_mock = self.git_patcher.start()

        self.git_path = tempfile.mkdtemp()
        git_instance_mock = PropertyMock()
        git_instance_mock.return_value.path = self.git_path
        self.git_mock.side_effect = git_instance_mock

    def get_mocked_job(self, design_class: Type[DesignJob]):
        """Create an instance of design_class and properly mock request and job_result for testing."""
        job_model, _ = refresh_job_model_from_job_class(Job, "plugins", design_class)
        job = design_class()
        job.job_result = JobResult.objects.create(
            name="Fake Job Result",
            obj_type=ContentType.objects.get_for_model(job_model),
            job_model=job_model,
            job_id=uuid.uuid4(),
        )
        job.save_design_file = lambda filename, content: None
        job.request = mock.Mock()
        self.logged_messages = []

        def record_log(message, obj, level_choice, grouping=None, logger=None):  # pylint: disable=unused-argument
            self.logged_messages.append(
                {
                    "message": message,
                    "obj": obj,
                    "level_choice": level_choice,
                    "grouping": grouping,
                }
            )

        job.job_result.log = mock.Mock()
        job.job_result.log.side_effect = record_log
        return job

    def assert_context_files_created(self, *filenames):
        """Confirm that the list of filenames were created as part of the design implementation."""
        for filename in filenames:
            self.assertTrue(path.exists(path.join(self.git_path, filename)), f"{filename} was not created")

    def assertJobSuccess(self, job):  # pylint: disable=invalid-name
        """Assert that a mocked job has completed successfully."""
        if job.failed:
            self.fail(f"Job failed with {self.logged_messages[-1]}")

    def tearDown(self):
        """Remove temporary files."""
        self.git_patcher.stop()
        shutil.rmtree(self.git_path)
        super().tearDown()
