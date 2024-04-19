"""Test running design jobs."""

import copy
from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Manufacturer, DeviceType, Device
from nautobot.ipam.models import VRF, Prefix, IPAddress

from nautobot.extras.models import JobResult, Job, Status
from nautobot_design_builder.errors import DesignImplementationError, DesignValidationError
from nautobot_design_builder.tests import DesignTestCase
from nautobot_design_builder.tests.designs import test_designs
from nautobot_design_builder.util import nautobot_version
from nautobot_design_builder import models


# pylint: disable=unused-argument


class TestDesignJob(DesignTestCase):
    """Test running design jobs."""

    @patch("nautobot_design_builder.models.Journal")
    @patch("nautobot_design_builder.models.DesignInstance.objects.get")
    @patch("nautobot_design_builder.design_job.DesignJob.design_model")
    @patch("nautobot_design_builder.design_job.Builder")
    def test_simple_design_commit(self, object_creator: Mock, design_model_mock, design_instance_mock, journal_mock):
        job = self.get_mocked_job(test_designs.SimpleDesign)
        job.run(data=self.data, commit=True)
        self.assertIsNotNone(job.job_result)
        object_creator.assert_called()
        self.assertDictEqual(
            {"manufacturers": {"name": "Test Manufacturer"}},
            job.designs[test_designs.SimpleDesign.Meta.design_file],
        )
        object_creator.return_value.roll_back.assert_not_called()

    @patch("nautobot_design_builder.models.Journal")
    @patch("nautobot_design_builder.models.DesignInstance.objects.get")
    @patch("nautobot_design_builder.design_job.DesignJob.design_model")
    def test_simple_design_report(self, design_model_mock, design_instance_mock, journal_mock):
        job = self.get_mocked_job(test_designs.SimpleDesignReport)
        job.run(data=self.data, commit=True)
        self.assertJobSuccess(job)
        self.assertEqual("Report output", job.job_result.data["report"])  # pylint: disable=unsubscriptable-object

    @patch("nautobot_design_builder.models.Journal")
    @patch("nautobot_design_builder.models.DesignInstance.objects.get")
    @patch("nautobot_design_builder.design_job.DesignJob.design_model")
    def test_multiple_design_files(self, design_model_mock, design_instance_mock, journal_mock):
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

    @patch("nautobot_design_builder.models.Journal")
    @patch("nautobot_design_builder.models.DesignInstance.objects.get")
    @patch("nautobot_design_builder.design_job.DesignJob.design_model")
    def test_multiple_design_files_with_roll_back(self, design_model_mock, design_instance_mock, journal_mock):
        self.assertEqual(0, Manufacturer.objects.all().count())
        job = self.get_mocked_job(test_designs.MultiDesignJobWithError)
        if nautobot_version < "2":
            job.run(data=self.data, commit=True)
        else:
            self.assertRaises(DesignValidationError, job.run, data={}, commit=True)

        self.assertEqual(0, Manufacturer.objects.all().count())

    @patch("nautobot_design_builder.models.Journal")
    @patch("nautobot_design_builder.models.DesignInstance.objects.get")
    @patch("nautobot_design_builder.design_job.DesignJob.design_model")
    @patch("nautobot_design_builder.design_job.Builder")
    def test_custom_extensions(self, builder_patch: Mock, design_model_mock, design_instance_mock, journal_mock):
        job = self.get_mocked_job(test_designs.DesignJobWithExtensions)
        job.run(data=self.data, commit=True)
        builder_patch.assert_called_once_with(
            job_result=job.job_result,
            extensions=test_designs.DesignJobWithExtensions.Meta.extensions,
            journal=journal_mock(),
        )


class TestDesignJobLogging(DesignTestCase):
    """Test that the design job logs errors correctly."""

    @patch("nautobot_design_builder.models.Journal")
    @patch("nautobot_design_builder.models.DesignInstance.objects.get")
    @patch("nautobot_design_builder.design_job.DesignJob.design_model")
    @patch("nautobot_design_builder.design_job.Builder")
    def test_simple_design_implementation_error(
        self, object_creator: Mock, design_model_mock, design_instance_mock, journal_mock
    ):
        object_creator.return_value.implement_design_changes.side_effect = DesignImplementationError("Broken")
        job = self.get_mocked_job(test_designs.SimpleDesign)
        if nautobot_version < "2":
            job.run(data=self.data, commit=True)
        else:
            self.assertRaises(DesignImplementationError, job.run, data={}, commit=True)
        self.assertTrue(job.failed)
        job.job_result.log.assert_called()
        self.assertEqual("Broken", self.logged_messages[-1]["message"])

    @patch("nautobot_design_builder.models.Journal")
    @patch("nautobot_design_builder.models.DesignInstance.objects.get")
    @patch("nautobot_design_builder.design_job.DesignJob.design_model")
    def test_invalid_ref(self, design_model_mock, design_instance_mock, journal_mock):
        job = self.get_mocked_job(test_designs.DesignWithRefError)
        if nautobot_version < "2":
            job.run(data=self.data, commit=True)
        else:
            self.assertRaises(DesignImplementationError, job.run, data={}, commit=True)
        message = self.logged_messages[-1]["message"]
        self.assertEqual("No ref named manufacturer has been saved in the design.", message)

    @patch("nautobot_design_builder.models.Journal")
    @patch("nautobot_design_builder.models.DesignInstance.objects.get")
    @patch("nautobot_design_builder.design_job.DesignJob.design_model")
    def test_failed_validation(self, design_model_mock, design_instance_mock, journal_mock):
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


class TestDesignJobIntegration(DesignTestCase):
    """Test to validate the whole end to end create and update design life cycle."""

    def setUp(self):
        """Per-test setup."""
        super().setUp()
        if nautobot_version < "2.0.0":
            from nautobot.dcim.models import Site, DeviceRole  # pylint: disable=import-outside-toplevel
        else:
            self.skipTest("These tests are only supported in Nautobot 1.x")

        site = Site.objects.create(name="test site")
        manufacturer = Manufacturer.objects.create(name="test manufacturer")
        device_type = DeviceType.objects.create(model="test-device-type", manufacturer=manufacturer)
        device_role = DeviceRole.objects.create(name="test role")
        self.device1 = Device.objects.create(
            name="test device 1",
            device_type=device_type,
            site=site,
            device_role=device_role,
            status=Status.objects.get(name="Active"),
        )
        self.device2 = Device.objects.create(
            name="test device 2",
            device_type=device_type,
            site=site,
            device_role=device_role,
            status=Status.objects.get(name="Active"),
        )
        self.device3 = Device.objects.create(
            name="test device 3",
            device_type=device_type,
            site=site,
            device_role=device_role,
            status=Status.objects.get(name="Active"),
        )

        # Setup the Job and Design object to run a Design Deployment
        self.job_instance = self.get_mocked_job(test_designs.IntegrationDesign)
        job = Job.objects.create(name="Integration Design")
        self.job_instance.job_result = JobResult.objects.create(
            name="Fake Integration Design Job Result",
            obj_type=ContentType.objects.get_for_model(Job),
            job_id=job.id,
        )
        self.job_instance.job_result.log = Mock()
        self.job_instance.job_result.job_model = job

        # This is done via signals when Jobs are synchronized
        models.Design.objects.get_or_create(job=job)

    def test_create_integration_design(self):
        """Test to validate the first creation of the design."""

        self.data["ce"] = self.device1
        self.data["pe"] = self.device2
        self.data["customer_name"] = "customer 1"

        self.job_instance.run(data=self.data, commit=True)

        self.assertEqual(VRF.objects.first().name, "64501:1")
        self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.0/24").prefix), "192.0.2.0/24")
        self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.0/30").prefix), "192.0.2.0/30")
        self.assertEqual(Prefix.objects.get(prefix="192.0.2.0/30").vrf, VRF.objects.first())
        self.assertEqual(
            Device.objects.get(name=self.device1.name).interfaces.first().cable,
            Device.objects.get(name=self.device2.name).interfaces.first().cable,
        )
        self.assertEqual(
            IPAddress.objects.get(host="192.0.2.1").assigned_object,
            Device.objects.get(name=self.device1.name).interfaces.first(),
        )
        self.assertEqual(
            IPAddress.objects.get(host="192.0.2.2").assigned_object,
            Device.objects.get(name=self.device2.name).interfaces.first(),
        )

    def test_update_integration_design(self):
        """Test to validate the update of the design."""
        original_data = copy.copy(self.data)

        # This part reproduces the creation of the design on the first iteration
        self.data["ce"] = self.device1
        self.data["pe"] = self.device2
        self.data["customer_name"] = "customer 1"
        self.job_instance.run(data=self.data, commit=True)

        # This is a second, and third run with new input to update the deployment
        for _ in range(2):
            data = copy.copy(original_data)
            data["ce"] = self.device3
            data["pe"] = self.device2
            data["customer_name"] = "customer 2"
            self.job_instance.run(data=data, commit=True)

            self.assertEqual(VRF.objects.first().name, "64501:2")
            self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.0/24").prefix), "192.0.2.0/24")
            self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.0/30").prefix), "192.0.2.0/30")
            self.assertEqual(Prefix.objects.get(prefix="192.0.2.0/30").vrf, VRF.objects.first())
            self.assertEqual(
                Device.objects.get(name=self.device3.name).interfaces.first().cable,
                Device.objects.get(name=self.device2.name).interfaces.first().cable,
            )
            self.assertEqual(
                IPAddress.objects.get(host="192.0.2.1").assigned_object,
                Device.objects.get(name=self.device3.name).interfaces.first(),
            )
            self.assertEqual(
                IPAddress.objects.get(host="192.0.2.2").assigned_object,
                Device.objects.get(name=self.device2.name).interfaces.first(),
            )
