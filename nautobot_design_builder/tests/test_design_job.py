"""Test running design jobs."""

import copy
from unittest.mock import patch, Mock, ANY, MagicMock

from django.core.exceptions import ValidationError

from nautobot.dcim.models import Manufacturer, DeviceType, Device, Site, DeviceRole
from nautobot.ipam.models import VRF, Prefix, IPAddress

from nautobot.extras.models import Status
from nautobot_design_builder.models import Deployment, ChangeRecord
from nautobot_design_builder.errors import DesignImplementationError, DesignValidationError
from nautobot_design_builder.tests import DesignTestCase
from nautobot_design_builder.tests.designs import test_designs


# pylint: disable=unused-argument


class TestDesignJob(DesignTestCase):
    """Test running design jobs."""

    def test_simple_design_rollback(self):
        """Confirm that database changes are rolled back when an exception is raised."""
        self.assertEqual(0, Manufacturer.objects.all().count())
        job = self.get_mocked_job(test_designs.MultiDesignJobWithError)
        job.run(data=self.data, commit=True)
        self.assertEqual(0, Manufacturer.objects.all().count())

    def test_simple_design_rollback_deployment_mode(self):
        """Confirm that database changes are rolled back when an exception is raised and no Design Deployment is created."""
        self.assertEqual(0, Manufacturer.objects.all().count())
        job = self.get_mocked_job(test_designs.DesignJobModeDeploymentWithError)
        job.run(data={**self.data, **{"deployment_name": "whatever"}}, commit=True)
        self.assertEqual(0, Manufacturer.objects.all().count())
        self.assertEqual(0, Deployment.objects.all().count())

    def test_simple_design_report(self):
        """Confirm that a report is generated."""
        job = self.get_mocked_job(test_designs.SimpleDesignReport)
        job.run(data=self.data, commit=True)
        self.assertJobSuccess(job)
        self.assertEqual("Report output", job.report)

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
        job.run(data=self.data, commit=True)

        self.assertEqual(0, Manufacturer.objects.all().count())

    @patch("nautobot_design_builder.design_job.Environment")
    def test_custom_extensions(self, environment: Mock):
        job = self.get_mocked_job(test_designs.DesignJobWithExtensions)
        job.run(data=self.data, commit=True)
        environment.assert_called_once_with(
            job_result=job.job_result,
            extensions=test_designs.DesignJobWithExtensions.Meta.extensions,
            change_set=ANY,
            import_mode=False,
        )

    def test_import_design_create_or_update(self):
        """Confirm that existing data can be imported with 'create_or_update'."""
        job = self.get_mocked_job(test_designs.SimpleDesignDeploymentMode)

        # The object to be imported by the design deployment already exists
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer")
        self.data["import_mode"] = True
        self.data["deployment_name"] = "deployment name example"
        job.run(data=self.data, commit=True)
        self.assertJobSuccess(job)
        self.assertEqual(Deployment.objects.first().name, "deployment name example")
        self.assertEqual(ChangeRecord.objects.first().design_object, manufacturer)
        self.assertEqual(ChangeRecord.objects.first().design_object.description, "Test description")

        # Running the import twice for a 'create_or_update' operation should raise an exception
        job = self.get_mocked_job(test_designs.SimpleDesignDeploymentMode)
        self.data["deployment_name"] = "another deployment name example"
        with self.assertRaises(ValueError) as error:
            job.run(data=self.data, commit=True)
        self.assertEqual(
            str(error.exception),
            "The description attribute for Test Manufacturer is already owned by Design Deployment Simple Design in deployment mode with create_or_update - deployment name example",
        )

    def test_import_design_update(self):
        """Confirm that existing data can be imported with 'update'."""
        job = self.get_mocked_job(test_designs.SimpleDesignDeploymentModeUpdate)

        # The object to be imported by the design deployment already exists
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer", description="old description")
        self.data["import_mode"] = True
        self.data["deployment_name"] = "deployment name example"
        job.run(data=self.data, commit=True)
        self.assertJobSuccess(job)
        self.assertEqual(Deployment.objects.first().name, "deployment name example")
        self.assertEqual(ChangeRecord.objects.first().design_object, manufacturer)
        self.assertEqual(ChangeRecord.objects.first().design_object.description, "Test description")

        # Running the import twice for a 'update' operation should raise an exception when attribute conflict
        job = self.get_mocked_job(test_designs.SimpleDesignDeploymentModeUpdate)
        self.data["deployment_name"] = "another deployment name example"
        with self.assertRaises(ValueError) as error:
            job.run(data=self.data, commit=True)
        self.assertEqual(
            str(error.exception),
            "The description attribute for Test Manufacturer is already owned by Design Deployment Simple Design in deployment mode with update - deployment name example",
        )

    def test_import_design_multiple_objects(self):
        """Confirming that multiple, interrelated objects can be imported."""
        job = self.get_mocked_job(test_designs.SimpleDesignDeploymentModeMultipleObjects)

        # Create data initially
        self.data["deployment_name"] = "I will be deleted"
        job.run(data=self.data, commit=True)
        self.assertJobSuccess(job)

        # Unlink the objects from the deployment so that they can be re-imported
        deployment = Deployment.objects.get(name=self.data["deployment_name"])
        deployment.decommission(local_logger=MagicMock(), delete=False)
        deployment.delete()

        self.data["import_mode"] = True
        self.data["deployment_name"] = "I will persist"
        job.run(data=self.data, commit=True)

        self.assertJobSuccess(job)
        self.assertEqual(ChangeRecord.objects.count(), 6)
        self.assertTrue(ChangeRecord.objects.filter_by_design_object_id(Device.objects.first().pk).exists())


class TestDesignJobLogging(DesignTestCase):
    """Test that the design job logs errors correctly."""

    @patch("nautobot_design_builder.design_job.Environment")
    def test_simple_design_implementation_error(self, environment: Mock):
        environment.return_value.implement_design.side_effect = DesignImplementationError("Broken")
        job = self.get_mocked_job(test_designs.SimpleDesign)
        job.run(data=self.data, commit=True)
        self.assertTrue(job.failed)
        job.job_result.log.assert_called()
        self.assertEqual("Broken", self.logged_messages[-1]["message"])

    def test_invalid_ref(self):
        job = self.get_mocked_job(test_designs.DesignWithRefError)
        job.run(data=self.data, commit=True)
        message = self.logged_messages[-1]["message"]
        self.assertEqual("No ref named manufacturer has been saved in the design.", message)

    def test_failed_validation(self):
        job = self.get_mocked_job(test_designs.DesignWithValidationError)
        job.run(data=self.data, commit=True)
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
        self.data["deployment_name"] = "Test Design"
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

    def test_create_integration_design(self):
        """Test to validate the first creation of the design."""

        self.data["device_b"] = self.device1
        self.data["device_a"] = self.device2
        self.data["customer_name"] = "customer 1"

        job = self.get_mocked_job(test_designs.IntegrationDesign)
        job.run(data=self.data, commit=True)
        self.assertJobSuccess(job)

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

    def test_create_integration_design_twice(self):
        """Test to validate the second deployment of a design."""

        self.data["device_b"] = self.device1
        self.data["device_a"] = self.device2
        self.data["customer_name"] = "customer 1"

        job = self.get_mocked_job(test_designs.IntegrationDesign)
        job.run(data=self.data, commit=True)
        self.assertJobSuccess(job)

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

        self.data["deployment_name"] = "another deployment"
        self.data["device_b"] = self.device1
        self.data["device_a"] = self.device2
        self.data["customer_name"] = "customer 1"

        job = self.get_mocked_job(test_designs.IntegrationDesign)
        job.run(data=self.data, commit=True)
        self.assertJobSuccess(job)

        self.assertEqual(VRF.objects.first().name, "64501:1")
        Prefix.objects.get(prefix="192.0.2.4/30")

    def test_update_integration_design(self):
        """Test to validate the update of the design."""
        original_data = copy.copy(self.data)

        # This part reproduces the creation of the design on the first iteration
        self.data["device_b"] = self.device1
        self.data["device_a"] = self.device2
        self.data["customer_name"] = "customer 1"
        job = self.get_mocked_job(test_designs.IntegrationDesign)
        job.run(data=self.data, commit=True)
        self.assertJobSuccess(job)

        # This is a second, and third run with new input to update the deployment
        for i in range(2):
            data = copy.copy(original_data)
            if i == 0:
                data["device_b"] = self.device3
                data["device_a"] = self.device2
            else:
                data["device_b"] = self.device3
                data["device_a"] = self.device1

            data["customer_name"] = "customer 2"

            job = self.get_mocked_job(test_designs.IntegrationDesign)
            job.run(data=data, commit=True)
            self.assertJobSuccess(job)
            self.assertEqual(VRF.objects.first().name, "64501:2")
            self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.0/24").prefix), "192.0.2.0/24")
            self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.4/30").prefix), "192.0.2.4/30")
            self.assertEqual(Prefix.objects.get(prefix="192.0.2.4/30").vrf, VRF.objects.first())

            self.assertEqual(
                data["device_a"].interfaces.first().cable,
                data["device_b"].interfaces.first().cable,
            )
            self.assertEqual(
                IPAddress.objects.get(host="192.0.2.6").assigned_object,
                data["device_a"].interfaces.first(),
            )

            self.assertEqual(
                IPAddress.objects.get(host="192.0.2.5").assigned_object,
                data["device_b"].interfaces.first(),
            )
