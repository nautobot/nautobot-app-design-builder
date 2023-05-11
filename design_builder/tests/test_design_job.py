"""Test running design jobs."""
from unittest import mock
from unittest.mock import patch

from nautobot.dcim.models import Site

from design_builder.errors import DesignImplementationError, DesignValidationError
from design_builder.tests import DesignTestCase
from design_builder.tests.designs import test_designs


class TestDesignJob(DesignTestCase):
    @patch("design_builder.base.Builder")
    def test_simple_design_commit(self, object_creator: mock.Mock):
        job = self.get_mocked_job(test_designs.SimpleDesign)
        job.run({}, True)
        self.assertIsNotNone(job.job_result)
        object_creator.assert_called()
        self.assertDictEqual(
            {"sites": {"name": "Test Site", "status__name": "Active"}}, job.designs[test_designs.SimpleDesign.Meta.design_file]
        )
        object_creator.return_value.roll_back.assert_not_called()

    @patch("design_builder.base.Builder")
    def test_simple_design_implementation_error(self, object_creator: mock.Mock):
        object_creator.return_value.implement_design.side_effect = DesignImplementationError("Broken")
        job = self.get_mocked_job(test_designs.SimpleDesign)
        job.run({}, True)
        self.assertTrue(job.failed)
        job.job_result.log.assert_called()
        self.assertEqual("Failed to implement design: Broken", job.job_result.log.call_args.args[0])

    def test_simple_design_report(self):
        job = self.get_mocked_job(test_designs.SimpleDesignReport)
        job.run({}, True)
        self.assertEqual("Report output", job.results["report"])  # pylint: disable=unsubscriptable-object

    def test_multiple_design_files(self):
        job = self.get_mocked_job(test_designs.MultiDesignJob)
        job.run({}, True)
        self.assertDictEqual(
            {"sites": {"name": "Test Site", "status__name": "Active"}}, job.designs[test_designs.MultiDesignJob.Meta.design_files[0]]
        )
        self.assertDictEqual(
            {"sites": {"name": "Test Site 1", "status__name": "Active"}},
            job.designs[test_designs.MultiDesignJob.Meta.design_files[1]],
        )

    def test_multiple_design_files_with_roll_back(self):
        self.assertEqual(0, Site.objects.all().count())
        job = self.get_mocked_job(test_designs.MultiDesignJobWithError)
        self.assertRaises(DesignValidationError, job.run, {}, True)
        self.assertEqual(0, Site.objects.all().count())
