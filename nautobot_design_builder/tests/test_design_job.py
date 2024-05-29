"""Test running design jobs."""

import copy
import unittest
from unittest.mock import patch, Mock, ANY

from django.core.exceptions import ValidationError

from nautobot.dcim.models import Manufacturer, DeviceType, Device
from nautobot.ipam.models import VRF, Prefix, IPAddress

from nautobot.extras.models import Status
from nautobot_design_builder.errors import DesignImplementationError, DesignValidationError
from nautobot_design_builder.tests import DesignTestCase
from nautobot_design_builder.tests.designs import test_designs


# pylint: disable=unused-argument


class TestDesignJob(DesignTestCase):
    """Test running design jobs."""

    @patch("nautobot_design_builder.design_job.Environment")
    def test_simple_design_commit(self, environment: Mock):
        job = self.get_mocked_job(test_designs.SimpleDesign)
        job.run(data={}, dryrun=False)
        self.assertIsNotNone(job.job_result)
        environment.assert_called()
        self.assertDictEqual(
            {
                "manufacturers": [
                    {"name": "Test Manufacturer"},
                    {"!create:name": "Test Manufacturer Explicit !create"},
                ]
            },
            job.designs[test_designs.SimpleDesign.Meta.design_file],
        )
        environment.return_value.roll_back.assert_not_called()

    def test_simple_design_rollback(self):
        job1 = self.get_mocked_job(test_designs.SimpleDesign)
        job1.run(data={}, dryrun=False)
        self.assertEqual(2, Manufacturer.objects.all().count())
        job2 = self.get_mocked_job(test_designs.SimpleDesign3)
        self.assertRaises(DesignValidationError, job2.run, data={}, dryrun=False)
        self.assertEqual(2, Manufacturer.objects.all().count())

    def test_simple_design_with_post_implementation(self):
        job = self.get_mocked_job(test_designs.SimpleDesignWithPostImplementation)
        job.run(data={}, dryrun=False)
        self.assertTrue(getattr(job, "post_implementation_called"))

    def test_simple_design_report(self):
        """Confirm that a report is generated."""
        job = self.get_mocked_job(test_designs.SimpleDesignReport)
        job.run(data=self.data, commit=True)
        self.assertJobSuccess(job)
        self.assertEqual("Report output", job.report)

    def test_multiple_design_files(self):
        job = self.get_mocked_job(test_designs.MultiDesignJob)
        job.run(dryrun=False, **self.data)
        self.assertDictEqual(
            {
                "manufacturers": [
                    {"name": "Test Manufacturer"},
                    {"!create:name": "Test Manufacturer Explicit !create"},
                ]
            },
            job.designs[test_designs.MultiDesignJob.Meta.design_files[0]],
        )
        self.assertDictEqual(
            {"manufacturers": {"name": "Test Manufacturer 1"}},
            job.designs[test_designs.MultiDesignJob.Meta.design_files[1]],
        )

    def test_multiple_design_files_with_roll_back(self):
        self.assertEqual(0, Manufacturer.objects.all().count())
        job = self.get_mocked_job(test_designs.MultiDesignJobWithError)
        self.assertRaises(DesignValidationError, job.run, dryrun=False, **self.data)

        self.assertEqual(0, Manufacturer.objects.all().count())

    @patch("nautobot_design_builder.design_job.Environment")
    def test_custom_extensions(self, environment: Mock):
        job = self.get_mocked_job(test_designs.DesignJobWithExtensions)
        job.run(dryrun=False, **self.data)
        environment.assert_called_once_with(
            job_result=job.job_result,
            extensions=test_designs.DesignJobWithExtensions.Meta.extensions,
            change_set=ANY,
        )


class TestDesignJobLogging(DesignTestCase):
    """Test that the design job logs errors correctly."""

    @patch("nautobot_design_builder.design_job.Environment")
    def test_simple_design_implementation_error(self, environment: Mock):
        environment.return_value.implement_design.side_effect = DesignImplementationError("Broken")
        job = self.get_mocked_job(test_designs.SimpleDesign)
        self.assertRaises(DesignImplementationError, job.run, dryrun=False, **self.data)
        job.job_result.log.assert_called()
        self.assertEqual("Broken", self.logged_messages[-1]["message"])

    def test_invalid_ref(self):
        job = self.get_mocked_job(test_designs.DesignWithRefError)
        self.assertRaises(DesignImplementationError, job.run, dryrun=False, **self.data)
        message = self.logged_messages[-1]["message"]
        self.assertEqual("No ref named manufacturer has been saved in the design.", message)

    def test_failed_validation(self):
        job = self.get_mocked_job(test_designs.DesignWithValidationError)
        want_error = DesignValidationError("Manufacturer")
        want_error.__cause__ = ValidationError(
            {
                "name": "This field cannot be blank.",
            }
        )
        with self.assertRaises(DesignValidationError) as raised:
            job.run(dryrun=False, **self.data)

        self.assertEqual(str(want_error), str(raised.exception))


class TestDesignJobIntegration(DesignTestCase):
    """Test to validate the whole end to end create and update design life cycle."""

    def setUp(self):
        """Per-test setup."""
        super().setUp()
        self.skipTest("These tests are only supported in Nautobot 1.x")

        site = Site.objects.create(name="test site")  # noqa:F821  # pylint:disable=undefined-variable
        manufacturer = Manufacturer.objects.create(name="test manufacturer")
        device_type = DeviceType.objects.create(model="test-device-type", manufacturer=manufacturer)
        device_role = DeviceRole.objects.create(name="test role")  # noqa:F821  # pylint:disable=undefined-variable
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

    def test_create_integration_design(self):
        """Test to validate the first creation of the design."""

        self.data["ce"] = self.device1
        self.data["pe"] = self.device2
        self.data["customer_name"] = "customer 1"

        job = self.get_mocked_job(test_designs.IntegrationDesign)
        job.run(data=self.data, commit=True)

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

    @unittest.skip("Feature not ready yet, depends on nextprefix logic.")
    def test_create_integration_design_twice(self):
        """Test to validate the second deployment of a design."""

        self.data["device_b"] = self.device1
        self.data["device_a"] = self.device2
        self.data["customer_name"] = "customer 1"

        job = self.get_mocked_job(test_designs.IntegrationDesign)
        job.run(data=self.data, commit=True)

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

        self.data["instance_name"] = "another deployment"
        self.data["device_b"] = self.device1
        self.data["device_a"] = self.device2
        self.data["customer_name"] = "customer 1"

        job = self.get_mocked_job(test_designs.IntegrationDesign)
        job.run(data=self.data, commit=True)

        self.assertEqual(VRF.objects.first().name, "64501:1")
        Prefix.objects.get(prefix="192.0.2.4/30")

    def test_update_integration_design(self):
        """Test to validate the update of the design."""
        original_data = copy.copy(self.data)

        # This part reproduces the creation of the design on the first iteration
        self.data["ce"] = self.device1
        self.data["pe"] = self.device2
        self.data["customer_name"] = "customer 1"
        job = self.get_mocked_job(test_designs.IntegrationDesign)
        job.run(data=self.data, commit=True)

        # This is a second, and third run with new input to update the deployment
        for _ in range(2):
            data = copy.copy(original_data)
            data["ce"] = self.device3
            data["pe"] = self.device2
            data["customer_name"] = "customer 2"

            job = self.get_mocked_job(test_designs.IntegrationDesign)
            job.run(data=data, commit=True)

            self.assertEqual(VRF.objects.first().name, "64501:2")
            self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.0/24").prefix), "192.0.2.0/24")
            self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.0/30").prefix), "192.0.2.0/30")
            self.assertEqual(Prefix.objects.get(prefix="192.0.2.0/30").vrf, VRF.objects.first())

            self.assertEqual(
                data["device_a"].interfaces.first().cable,
                data["device_b"].interfaces.first().cable,
            )
            self.assertEqual(
                IPAddress.objects.get(host="192.0.2.2").assigned_object,
                data["device_a"].interfaces.first(),
            )

            self.assertEqual(
                IPAddress.objects.get(host="192.0.2.1").assigned_object,
                data["device_b"].interfaces.first(),
            )
