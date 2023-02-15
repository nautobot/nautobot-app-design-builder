"""Unit tests for design_builder plugin."""

import logging
import shutil
import tempfile
from os import path
from typing import Type
from unittest import mock
from unittest.mock import PropertyMock, patch

from django.test import TestCase

from design_builder.base import DesignJob

logging.disable(logging.CRITICAL)


class DesignTestCase(TestCase):
    """DesignTestCase aides in creating unit tests for design jobs and templates."""

    def setUp(self):
        """Setup a mock git repo to watch for config context creation."""
        super().setUp()
        self.git_patcher = patch("design_builder.ext.GitRepo")
        self.git_mock = self.git_patcher.start()

        self.git_path = tempfile.mkdtemp()
        git_instance_mock = PropertyMock()
        git_instance_mock.return_value.path = self.git_path
        self.git_mock.side_effect = git_instance_mock

    def get_mocked_job(self, design_class: Type[DesignJob]):  # pylint: disable=no-self-use
        """Create an instance of design_class and properly mock request and job_result for testing."""
        job = design_class()
        job.request = mock.Mock()
        job.job_result = mock.Mock()
        return job

    def assert_context_files_created(self, *filenames):
        """Confirm that the list of filenames were created as part of the design implementation."""
        for filename in filenames:
            self.assertTrue(path.exists(path.join(self.git_path, filename)), f"{filename} was not created")

    def tearDown(self):
        """Remove temporary files."""
        self.git_patcher.stop()
        shutil.rmtree(self.git_path)
        super().tearDown()
