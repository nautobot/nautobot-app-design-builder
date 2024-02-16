"""Test running design jobs."""
from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError

from nautobot.dcim.models import Manufacturer

from nautobot_design_builder.errors import DesignImplementationError, DesignValidationError
from nautobot_design_builder.tests import DesignTestCase
from nautobot_design_builder.tests.designs import test_designs
from nautobot_design_builder.util import nautobot_version


class TestDesignJob(DesignTestCase):
    """Test running design jobs."""

    @patch("nautobot_design_builder.design_job.Builder")
    def test_simple_design_commit(self, object_creator: Mock):
        job = self.get_mocked_job(test_designs.SimpleDesign)
        job.run(data=self.data, commit=True)
        self.assertIsNotNone(job.job_result)
        object_creator.assert_called()
        self.assertDictEqual(
            {"manufacturers": {"name": "Test Manufacturer"}},
            job.designs[test_designs.SimpleDesign.Meta.design_file],
        )
        object_creator.return_value.roll_back.assert_not_called()

    def test_simple_design_report(self):
        job = self.get_mocked_job(test_designs.SimpleDesignReport)
        job.run(data=self.data, commit=True)
        self.assertJobSuccess(job)
        self.assertEqual("Report output", job.job_result.data["report"])  # pylint: disable=unsubscriptable-object

    def test_multiple_design_files(self):
        job = self.get_mocked_job(test_designs.MultiDesignJob)
        job.run(data=self.data, commit=True)
        self.assertDictEqual(
            {"manufacturers": {"name": "Test Manufacturer"}},
            job.designs[test_designs.MultiDesignJob.Meta.design_files[0]],
        )
        self.assertDictEqual(
            {"manufacturers": {"name": "Test Manufacturer 1"}},
            job.designs[test_designs.MultiDesignJob.Meta.design_files[1]],
        )

    def test_multiple_design_files_with_roll_back(self):
        self.assertEqual(0, Manufacturer.objects.all().count())
        job = self.get_mocked_job(test_designs.MultiDesignJobWithError)
        if nautobot_version < "2":
            job.run(data=self.data, commit=True)
        else:
            self.assertRaises(DesignValidationError, job.run, data={}, commit=True)

        self.assertEqual(0, Manufacturer.objects.all().count())

    @patch("nautobot_design_builder.design_job.Builder")
    def test_custom_extensions(self, builder_patch: Mock):
        job = self.get_mocked_job(test_designs.DesignJobWithExtensions)
        job.run(data=self.data, commit=True)
        builder_patch.assert_called_once_with(
            job_result=job.job_result, extensions=test_designs.DesignJobWithExtensions.Meta.extensions, journal=None
        )


class TestDesignJobLogging(DesignTestCase):
    """Test that the design job logs errors correctly."""

    @patch("nautobot_design_builder.design_job.Builder")
    def test_simple_design_implementation_error(self, object_creator: Mock):
        object_creator.return_value.implement_design.side_effect = DesignImplementationError("Broken")
        job = self.get_mocked_job(test_designs.SimpleDesign)
        if nautobot_version < "2":
            job.run(data=self.data, commit=True)
        else:
            self.assertRaises(DesignImplementationError, job.run, data={}, commit=True)
        self.assertTrue(job.failed)
        job.job_result.log.assert_called()
        self.assertEqual("Broken", self.logged_messages[-1]["message"])

    def test_invalid_ref(self):
        job = self.get_mocked_job(test_designs.DesignWithRefError)
        if nautobot_version < "2":
            job.run(data=self.data, commit=True)
        else:
            self.assertRaises(DesignImplementationError, job.run, data={}, commit=True)
        message = self.logged_messages[-1]["message"]
        self.assertEqual("No ref named manufacturer has been saved in the design.", message)

    def test_failed_validation(self):
        job = self.get_mocked_job(test_designs.DesignWithValidationError)
        if nautobot_version < "2":
            job.run(data=self.data, commit=True)
        else:
            self.assertRaises(DesignValidationError, job.run, data={}, commit=True)
        message = self.logged_messages[-1]["message"]

        want_error = DesignValidationError("Manufacturer")
        want_error.__cause__ = ValidationError(
            {
                "name": "This field cannot be blank.",
            }
        )
        self.assertEqual(str(want_error), message)
