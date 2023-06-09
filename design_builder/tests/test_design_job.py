"""Test running design jobs."""
from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError

from nautobot.dcim.models import Manufacturer

from design_builder.errors import DesignImplementationError, DesignValidationError
from design_builder.tests import DesignTestCase
from design_builder.tests.designs import test_designs


class TestDesignJob(DesignTestCase):
    @patch("design_builder.base.Builder")
    def test_simple_design_commit(self, object_creator: Mock):
        job = self.get_mocked_job(test_designs.SimpleDesign)
        job.run({}, True)
        self.assertIsNotNone(job.job_result)
        object_creator.assert_called()
        self.assertDictEqual(
            {"manufacturers": {"name": "Test Manufacturer"}},
            job.designs[test_designs.SimpleDesign.Meta.design_file],
        )
        object_creator.return_value.roll_back.assert_not_called()

    def test_simple_design_report(self):
        job = self.get_mocked_job(test_designs.SimpleDesignReport)
        job.run({}, True)
        self.assertJobSuccess(job)
        self.assertEqual("Report output", job.job_result.data["report"])  # pylint: disable=unsubscriptable-object

    def test_multiple_design_files(self):
        job = self.get_mocked_job(test_designs.MultiDesignJob)
        job.run({}, True)
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
        job.run({}, True)

        self.assertEqual(0, Manufacturer.objects.all().count())

    @patch("design_builder.base.Builder")
    def test_custom_extensions(self, builder_patch: Mock):
        job = self.get_mocked_job(test_designs.DesignJobWithExtensions)
        job.run({}, True)
        builder_patch.assert_called_once_with(
            job_result=job.job_result,
            extensions=test_designs.DesignJobWithExtensions.Meta.extensions,
        )


class TestDesignJobLogging(DesignTestCase):
    @patch("design_builder.base.Builder")
    def test_simple_design_implementation_error(self, object_creator: Mock):
        object_creator.return_value.implement_design.side_effect = DesignImplementationError("Broken")
        job = self.get_mocked_job(test_designs.SimpleDesign)
        job.run({}, True)
        self.assertTrue(job.failed)
        job.job_result.log.assert_called()
        self.assertEqual("Broken", self.logged_messages[-1]["message"])

    def test_invalid_ref(self):
        job = self.get_mocked_job(test_designs.DesignWithRefError)
        job.run({}, True)
        message = self.logged_messages[-1]["message"]
        self.assertEqual("No ref named manufacturer has been saved in the design.", message)

    def test_failed_validation(self):
        job = self.get_mocked_job(test_designs.DesignWithValidationError)
        job.run({}, True)
        message = self.logged_messages[-1]["message"]

        want_error = DesignValidationError("Manufacturer failed validation")
        want_error.__cause__ = ValidationError(
            {
                "name": "This field cannot be blank.",
            }
        )
        self.assertEqual(str(want_error), message)
