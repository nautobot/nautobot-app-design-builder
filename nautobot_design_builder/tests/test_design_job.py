"""Test running design jobs."""

import copy
import os
import sys
from unittest.mock import ANY, MagicMock, Mock, patch

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.transaction import TransactionManagementError
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.models import Role, Status
from nautobot.ipam.models import VRF, IPAddress, Prefix

from nautobot_design_builder.design_job import DesignJob
from nautobot_design_builder.errors import DesignImplementationError, DesignModelError, DesignValidationError
from nautobot_design_builder.models import ChangeRecord, Deployment
from nautobot_design_builder.testing import DesignTestCase, VerifyDesignTestCase
from nautobot_design_builder.tests.designs import test_designs

# pylint: disable=unused-argument,protected-access


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
        job.run(dryrun=False, **self.data)
        self.assertTrue(getattr(job, "post_implementation_called"))

    def test_simple_design_rollback_deployment_mode(self):
        """Confirm that database changes are rolled back when an exception is raised and no Design Deployment is created."""
        self.assertEqual(0, Manufacturer.objects.all().count())
        job = self.get_mocked_job(test_designs.DesignJobModeDeploymentWithError)
        self.assertRaises(DesignImplementationError, job.run, dryrun=False, **self.data)
        self.assertEqual(0, Manufacturer.objects.all().count())
        self.assertEqual(0, Deployment.objects.all().count())

    def test_simple_design_report(self):
        job = self.get_mocked_job(test_designs.SimpleDesignReport)
        job.run(data={}, dryrun=False)
        self.assertIn("simple_report.md", job.saved_files)  # pylint:disable=no-member
        self.assertEqual("Report output", job.saved_files["simple_report.md"])  # pylint:disable=no-member

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
            logger=job.logger,
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
        job.run(dryrun=False, **self.data)
        self.assertEqual(Deployment.objects.first().name, "deployment name example")
        self.assertEqual(ChangeRecord.objects.first().design_object, manufacturer)
        self.assertEqual(ChangeRecord.objects.first().design_object.description, "Test description")

        # Running the import twice for a 'create_or_update' operation should raise an exception
        job = self.get_mocked_job(test_designs.SimpleDesignDeploymentMode)
        self.data["deployment_name"] = "another deployment name example"
        manufacturer.description = "new description to show changes"
        manufacturer.save()
        with self.assertRaises(ValueError) as error:
            job.run(dryrun=False, **self.data)
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
        job.run(dryrun=False, **self.data)
        self.assertEqual(Deployment.objects.first().name, "deployment name example")
        self.assertEqual(ChangeRecord.objects.first().design_object, manufacturer)
        self.assertEqual(ChangeRecord.objects.first().design_object.description, "Test description")

        # Running the import twice for a 'update' operation should raise an exception when attribute conflict
        job = self.get_mocked_job(test_designs.SimpleDesignDeploymentModeUpdate)
        self.data["deployment_name"] = "another deployment name example"
        manufacturer.description = "new description to show changes"
        manufacturer.save()
        with self.assertRaises(ValueError) as error:
            job.run(dryrun=False, **self.data)
        self.assertEqual(
            str(error.exception),
            "The description attribute for Test Manufacturer is already owned by Design Deployment Simple Design in deployment mode with update - deployment name example",
        )

    def test_import_design_multiple_objects(self):
        """Confirming that multiple, interrelated objects can be imported."""
        job = self.get_mocked_job(test_designs.SimpleDesignDeploymentModeMultipleObjects)

        # Create data initially
        self.data["deployment_name"] = "I will be deleted"
        job.run(dryrun=False, **self.data)

        # Unlink the objects from the deployment so that they can be re-imported
        deployment = Deployment.objects.get(name=self.data["deployment_name"])
        deployment.decommission(local_logger=MagicMock(), delete=False)
        deployment.delete()

        self.data["import_mode"] = True
        self.data["deployment_name"] = "I will persist"
        job.run(dryrun=False, **self.data)

        self.assertEqual(ChangeRecord.objects.count(), 8)
        self.assertTrue(ChangeRecord.objects.filter_by_design_object_id(Device.objects.first().pk).exists())


class TestDesignJobLogging(DesignTestCase):
    """Test that the design job logs errors correctly."""

    @patch("nautobot_design_builder.design_job.Environment")
    def test_simple_design_implementation_error(self, environment: Mock):
        environment.return_value.implement_design.side_effect = DesignImplementationError("Broken")
        job = self.get_mocked_job(test_designs.SimpleDesign)
        self.assertRaises(DesignImplementationError, job.run, dryrun=False, **self.data)
        self.assertTrue(bool(self.logged_messages))
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


class TestDesignJobRollbackErrorReporting(DesignTestCase):
    """Regression tests for surfacing the original error during rollback (issue #295).

    When a design fails and the transaction is already in a broken state, the
    `transaction.savepoint_rollback` that cleans up used to raise its own
    `TransactionManagementError` and completely mask the root cause. These tests
    confirm the underlying error is now surfaced instead of being swallowed.
    """

    def test_safe_savepoint_rollback_success_reraises_nothing(self):
        """When the rollback succeeds the helper is a no-op (caller re-raises the original error)."""
        with patch("nautobot_design_builder.design_job.transaction.savepoint_rollback") as mock_rollback:
            original = DesignImplementationError("Original design failure")
            # Should not raise; the caller is responsible for re-raising the original error.
            self.assertIsNone(DesignJob._safe_savepoint_rollback("sid_xyz", original))
        mock_rollback.assert_called_once_with("sid_xyz")

    def test_safe_savepoint_rollback_surfaces_original_error(self):
        """When the rollback itself fails, the original error must be surfaced, not masked."""
        original = ValidationError({"tagged_vlans": ["Mode must be set to tagged when specifying tagged_vlans"]})
        with patch(
            "nautobot_design_builder.design_job.transaction.savepoint_rollback",
            side_effect=TransactionManagementError(
                "An error occurred in the current transaction. You can't execute queries "
                "until the end of the 'atomic' block."
            ),
        ):
            with self.assertRaises(RuntimeError) as raised:
                DesignJob._safe_savepoint_rollback("sid_xyz", original)

        message = str(raised.exception)
        # The root cause must be visible in the message ...
        self.assertIn("Original error (ValidationError)", message)
        self.assertIn("tagged_vlans", message)
        # ... and so should the rollback failure (reviewer feedback on PR #296).
        self.assertIn("Rollback also failed (TransactionManagementError)", message)
        # The original exception is chained for full traceback context.
        self.assertIs(raised.exception.__cause__, original)

    @patch("nautobot_design_builder.design_job.Environment")
    def test_broken_transaction_surfaces_design_implementation_error(self, environment: Mock):
        """A failed rollback in the design-error branch surfaces the DesignImplementationError."""
        environment.return_value.implement_design.side_effect = DesignImplementationError("Original design failure")
        job = self.get_mocked_job(test_designs.SimpleDesign)
        with patch(
            "nautobot_design_builder.design_job.transaction.savepoint_rollback",
            side_effect=TransactionManagementError("broken transaction"),
        ):
            with self.assertRaises(RuntimeError) as raised:
                job.run(dryrun=False, **self.data)

        self.assertIn("Original design failure", str(raised.exception))
        self.assertIsInstance(raised.exception.__cause__, DesignImplementationError)

    @patch("nautobot_design_builder.design_job.Environment")
    def test_broken_transaction_surfaces_generic_error(self, environment: Mock):
        """A failed rollback in the generic-exception branch surfaces the original error."""
        environment.return_value.implement_design.side_effect = ValidationError(
            {"tagged_vlans": ["Mode must be set to tagged when specifying tagged_vlans"]}
        )
        job = self.get_mocked_job(test_designs.SimpleDesign)
        with patch(
            "nautobot_design_builder.design_job.transaction.savepoint_rollback",
            side_effect=TransactionManagementError("broken transaction"),
        ):
            with self.assertRaises(RuntimeError) as raised:
                job.run(dryrun=False, **self.data)

        message = str(raised.exception)
        self.assertIn("Original error (ValidationError)", message)
        self.assertIn("tagged_vlans", message)
        self.assertIsInstance(raised.exception.__cause__, ValidationError)

    @patch("nautobot_design_builder.design_job.Environment")
    def test_successful_rollback_still_raises_original_error(self, environment: Mock):
        """When rollback succeeds, the original error type must be preserved (no masking, no RuntimeError)."""
        environment.return_value.implement_design.side_effect = DesignModelError("Broken model")
        job = self.get_mocked_job(test_designs.SimpleDesign)
        # No savepoint patching: the real rollback succeeds, so the original error propagates unchanged.
        self.assertRaises(DesignModelError, job.run, dryrun=False, **self.data)


class TestDesignJobIntegration(DesignTestCase):
    """Test to validate the whole end to end create and update design life cycle."""

    def setUp(self):
        """Per-test setup."""
        super().setUp()
        self.data["deployment_name"] = "Test Design"
        location_type = LocationType.objects.create(name="Site")
        location_type.content_types.add(ContentType.objects.get_for_model(Device))
        site = Location.objects.create(
            name="test site",
            location_type=location_type,
            status=Status.objects.get(name="Active"),
        )
        manufacturer = Manufacturer.objects.create(name="test manufacturer")
        device_type = DeviceType.objects.create(model="test-device-type", manufacturer=manufacturer)
        device_role = Role.objects.create(name="test role")
        device_role.content_types.add(ContentType.objects.get_for_model(Device))
        self.device1 = Device.objects.create(
            name="test device 1",
            device_type=device_type,
            location=site,
            role=device_role,
            status=Status.objects.get(name="Active"),
        )
        self.device2 = Device.objects.create(
            name="test device 2",
            device_type=device_type,
            location=site,
            role=device_role,
            status=Status.objects.get(name="Active"),
        )
        self.device3 = Device.objects.create(
            name="test device 3",
            device_type=device_type,
            location=site,
            role=device_role,
            status=Status.objects.get(name="Active"),
        )

    def test_create_integration_design(self):
        """Test to validate the first creation of the design."""

        self.data["device_b"] = self.device1
        self.data["device_a"] = self.device2
        self.data["customer_name"] = "customer 1"

        job = self.get_mocked_job(test_designs.IntegrationDesign)
        job.run(dryrun=False, **self.data)

        self.assertEqual(VRF.objects.first().name, "customer 1")
        self.assertEqual(VRF.objects.first().rd, "64501:1")
        self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.0/24").prefix), "192.0.2.0/24")
        self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.0/30").prefix), "192.0.2.0/30")
        self.assertEqual(Prefix.objects.get(prefix="192.0.2.0/30").vrfs.first(), VRF.objects.first())
        self.assertEqual(
            Device.objects.get(name=self.device1.name).interfaces.first().cable,
            Device.objects.get(name=self.device2.name).interfaces.first().cable,
        )
        self.assertEqual(
            IPAddress.objects.get(host="192.0.2.1").interface_assignments.first().interface,
            Device.objects.get(name=self.device1.name).interfaces.first(),
        )
        self.assertEqual(
            IPAddress.objects.get(host="192.0.2.2").interface_assignments.first().interface,
            Device.objects.get(name=self.device2.name).interfaces.first(),
        )

    def test_create_integration_design_twice(self):
        """Test to validate the second deployment of a design."""

        self.data["device_b"] = self.device1
        self.data["device_a"] = self.device2
        self.data["customer_name"] = "customer 1"

        job = self.get_mocked_job(test_designs.IntegrationDesign)
        job.run(dryrun=False, **self.data)

        self.assertEqual(VRF.objects.first().name, "customer 1")
        self.assertEqual(VRF.objects.first().rd, "64501:1")
        self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.0/24").prefix), "192.0.2.0/24")
        self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.0/30").prefix), "192.0.2.0/30")
        self.assertEqual(Prefix.objects.get(prefix="192.0.2.0/30").vrfs.first(), VRF.objects.first())
        self.assertEqual(
            Device.objects.get(name=self.device1.name).interfaces.first().cable,
            Device.objects.get(name=self.device2.name).interfaces.first().cable,
        )
        self.assertEqual(
            IPAddress.objects.get(host="192.0.2.1").interface_assignments.first().interface,
            Device.objects.get(name=self.device1.name).interfaces.first(),
        )
        self.assertEqual(
            IPAddress.objects.get(host="192.0.2.2").interface_assignments.first().interface,
            Device.objects.get(name=self.device2.name).interfaces.first(),
        )

        self.data["deployment_name"] = "another deployment"
        self.data["device_b"] = self.device1
        self.data["device_a"] = self.device2
        self.data["customer_name"] = "customer 1"

        job = self.get_mocked_job(test_designs.IntegrationDesign)
        job.run(dryrun=False, **self.data)

        self.assertEqual(VRF.objects.first().name, "customer 1")
        self.assertEqual(VRF.objects.first().rd, "64501:1")
        Prefix.objects.get(prefix="192.0.2.4/30")

    def test_update_integration_design(self):
        """Test to validate the update of the design."""
        original_data = copy.copy(self.data)

        # This part reproduces the creation of the design on the first iteration
        data = {**original_data}
        data["device_b"] = self.device1
        data["device_a"] = self.device2
        data["customer_name"] = "customer 1"
        job = self.get_mocked_job(test_designs.IntegrationDesign)
        job.run(dryrun=False, **data)
        self.assertEqual(VRF.objects.first().rd, "64501:1")
        self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.0/24").prefix), "192.0.2.0/24")
        self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.0/30").prefix), "192.0.2.0/30")
        self.assertEqual(Prefix.objects.get(prefix="192.0.2.0/30").vrfs.first(), VRF.objects.first())

        self.assertEqual(
            data["device_a"].interfaces.first().cable,
            data["device_b"].interfaces.first().cable,
        )
        self.assertEqual(
            IPAddress.objects.get(host="192.0.2.2").interfaces.first(),
            data["device_a"].interfaces.first(),
        )

        self.assertEqual(
            IPAddress.objects.get(host="192.0.2.1").interfaces.first(),
            data["device_b"].interfaces.first(),
        )

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
            job.run(dryrun=False, **data)

            self.assertEqual(VRF.objects.first().rd, "64501:2")
            self.assertEqual(str(Prefix.objects.get(prefix="192.0.2.0/24").prefix), "192.0.2.0/24")
            self.assertEqual(Prefix.objects.get(prefix="192.0.2.0/30").vrfs.first(), VRF.objects.get(rd="64501:2"))

            self.assertEqual(
                data["device_a"].interfaces.first().cable,
                data["device_b"].interfaces.first().cable,
            )
            self.assertEqual(
                IPAddress.objects.get(host="192.0.2.2").interfaces.first(),
                data["device_a"].interfaces.first(),
            )

            self.assertEqual(
                IPAddress.objects.get(host="192.0.2.1").interfaces.first(),
                data["device_b"].interfaces.first(),
            )

            data["device_a"].refresh_from_db()
            self.assertIsNotNone(data["device_a"].local_config_context_data)


class TestDesignJobRenderMultipleInheritance(DesignTestCase):
    """Regression tests for DesignJob.render() with multiple inheritance (issue #287)."""

    @patch("nautobot_design_builder.design_job.new_template_environment")
    def test_render_does_not_raise_with_unrelated_mixin_as_first_base(self, mock_new_env):
        """render() must not raise AttributeError when a non-DesignJob mixin is __bases__[0]."""
        mock_new_env.return_value.get_template.return_value.render.return_value = "manufacturers: []"
        job = self.get_mocked_job(test_designs.SimpleDesignWithMixin)
        # Prior to the fix this raised: AttributeError: module 'builtins' has no attribute '__file__'
        job.render(MagicMock(), "templates/simple_design.yaml.j2")

    @patch("nautobot_design_builder.design_job.new_template_environment")
    def test_render_search_paths_include_design_class_directory(self, mock_new_env):
        """render() search paths must include the DesignJob subclass directory under multiple inheritance."""
        mock_new_env.return_value.get_template.return_value.render.return_value = "manufacturers: []"
        job = self.get_mocked_job(test_designs.SimpleDesignWithMixin)
        job.render(MagicMock(), "templates/simple_design.yaml.j2")

        search_paths = mock_new_env.call_args[0][1]
        expected_dir = os.path.dirname(sys.modules[test_designs.SimpleDesign.__module__].__file__)
        self.assertIn(expected_dir, search_paths)


class TestVerifyDesignJob(VerifyDesignTestCase):
    """Test running verify design jobs."""

    job_design = test_designs.VerifyDesign
    check_file = os.path.join(os.path.dirname(__file__), "checks", "verify_design.yaml")
    job_data = {"additional_manufacturer_1": "Manufacturer From Data"}

    def test_my_design(self):
        self.run_design_test()
