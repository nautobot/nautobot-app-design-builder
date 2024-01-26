"""Unit tests for nautobot_design_builder plugin."""

import logging
import shutil
import tempfile
from os import path
from typing import Type
from unittest import mock
from unittest.mock import PropertyMock, patch

from django.test import TestCase

from nautobot_design_builder.design_job import DesignJob
from nautobot_design_builder.util import nautobot_version

logging.disable(logging.CRITICAL)


class DesignTestCase(TestCase):
    """DesignTestCase aides in creating unit tests for design jobs and templates."""

    def setUp(self):
        """Setup a mock git repo to watch for config context creation."""
        super().setUp()
        self.logged_messages = []
        self.git_patcher = patch("nautobot_design_builder.ext.GitRepo")
        self.git_mock = self.git_patcher.start()

        self.git_path = tempfile.mkdtemp()
        git_instance_mock = PropertyMock()
        git_instance_mock.return_value.path = self.git_path
        self.git_mock.side_effect = git_instance_mock

    def get_mocked_job(self, design_class: Type[DesignJob]):
        """Create an instance of design_class and properly mock request and job_result for testing."""
        job = design_class()
        job.job_result = mock.Mock()
        if nautobot_version < "2.0.0":
            job.request = mock.Mock()
        else:
            job.job_result.data = {}
            old_run = job.run

            def new_run(data, commit):
                kwargs = {**data}
                kwargs["dryrun"] = not commit
                old_run(**kwargs)

            job.run = new_run
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
