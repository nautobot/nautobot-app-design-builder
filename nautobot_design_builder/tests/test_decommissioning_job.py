"""Decommissioning Tests."""

from unittest import mock

from django.contrib.contenttypes.models import ContentType
from nautobot.extras.models import JobResult, Secret, Status

from nautobot_design_builder import choices, models
from nautobot_design_builder.errors import DesignValidationError
from nautobot_design_builder.jobs import DeploymentDecommissioning
from nautobot_design_builder.tests.test_model_design import BaseDesignTest


def fake_ok(sender, deployment, **kwargs):  # pylint: disable=unused-argument
    """Fake function to return a pass for a hook."""
    return True, None


def fake_ko(sender, deployment, **kwargs):  # pylint: disable=unused-argument
    """Fake function to return a fail for a hook."""
    raise DesignValidationError("reason")


class DecommissionJobTestCase(BaseDesignTest):  # pylint: disable=too-many-instance-attributes
    """Test the DecommissionJobTestCase class."""

    job_class = DeploymentDecommissioning

    def setUp(self):
        """Per-test setup."""
        super().setUp()

        self.content_type = ContentType.objects.get_for_model(models.Deployment)

        # Decommissioning Job
        self.job = self.get_mocked_job(self.job_class)

        self.job.job_result = JobResult.objects.create(
            name="fake job",
            job_model=self.job.job_model,
        )
        self.job.job_result.log = mock.Mock()
        self.deployment = models.Deployment(
            design=self.designs[0],
            name="My Design 1",
            status=Status.objects.get(content_types=self.content_type, name=choices.DeploymentStatusChoices.ACTIVE),
            version=self.designs[0].version,
        )
        self.deployment.validated_save()

        self.deployment_2 = models.Deployment(
            design=self.designs[0],
            name="My Design 2",
            status=Status.objects.get(content_types=self.content_type, name=choices.DeploymentStatusChoices.ACTIVE),
            version=self.designs[0].version,
        )
        self.deployment_2.validated_save()

        self.initial_params = {"key1": "initial value"}
        self.changed_params = {"key1": "changed value"}
        self.secret = Secret.objects.create(
            name="test secret",
            provider="environment-variable",
            description="test description",
            parameters=self.changed_params,
        )
        self.secret.validated_save()

        kwargs = {
            "secret": f"{self.secret.pk}",
            "instance": "my instance",
        }

        self.job_result1 = JobResult.objects.create(
            name=self.jobs[0].name,
            job_model=self.jobs[0],
        )
        self.job_result1.job_kwargs = {"data": kwargs}
        self.job_result1.save()

        self.change_set1 = models.ChangeSet(deployment=self.deployment, job_result=self.job_result1)
        self.change_set1.validated_save()

        self.job_result2 = JobResult.objects.create(
            name=self.jobs[0].name,
            job_model=self.jobs[0],
            task_kwargs=kwargs,
        )

        self.change_set2 = models.ChangeSet(deployment=self.deployment_2, job_result=self.job_result2)
        self.change_set2.validated_save()

    def test_basic_decommission_run_with_full_control(self):
        self.assertEqual(1, Secret.objects.count())

        change_record = models.ChangeRecord.objects.create(
            change_set=self.change_set1,
            design_object=self.secret,
            full_control=True,
            index=self.change_set1._next_index(),  # pylint:disable=protected-access
        )
        change_record.validated_save()

        self.job.run(deployments=[self.deployment], delete=True)

        self.assertEqual(0, Secret.objects.count())

    def test_decommission_run_with_dependencies(self):
        self.assertEqual(1, Secret.objects.count())

        record_1 = models.ChangeRecord.objects.create(
            change_set=self.change_set1,
            design_object=self.secret,
            full_control=True,
            index=self.change_set1._next_index(),  # pylint:disable=protected-access
        )

        record_1.validated_save()

        record_2 = models.ChangeRecord.objects.create(
            change_set=self.change_set2,
            design_object=self.secret,
            full_control=False,
            changes={},
            index=self.change_set2._next_index(),  # pylint:disable=protected-access
        )
        record_2.validated_save()

        self.assertRaises(
            ValueError,
            self.job.run,
            deployments=[self.deployment],
            delete=True,
        )

        self.assertEqual(1, Secret.objects.count())

    def test_decommission_run_with_dependencies_but_decommissioned(self):
        self.assertEqual(1, Secret.objects.count())

        record_1 = models.ChangeRecord.objects.create(
            change_set=self.change_set1,
            design_object=self.secret,
            full_control=True,
            index=self.change_set1._next_index(),  # pylint:disable=protected-access
        )

        record_1.validated_save()

        record_2 = models.ChangeRecord.objects.create(
            change_set=self.change_set2,
            design_object=self.secret,
            full_control=False,
            changes={},
            index=self.change_set2._next_index(),  # pylint:disable=protected-access
        )
        record_2.validated_save()

        self.deployment_2.decommission()

        self.job.run(deployments=[self.deployment], delete=True)

        self.assertEqual(0, Secret.objects.count())

    def test_basic_decommission_run_without_full_control(self):
        self.assertEqual(1, Secret.objects.count())

        record_1 = models.ChangeRecord.objects.create(
            change_set=self.change_set1,
            design_object=self.secret,
            full_control=False,
            changes={},
            index=self.change_set1._next_index(),  # pylint:disable=protected-access
        )
        record_1.validated_save()

        self.job.run(deployments=[self.deployment], delete=True)

        self.assertEqual(1, Secret.objects.count())

    def test_decommission_run_without_full_control_string_value(self):
        self.assertEqual(1, Secret.objects.count())
        self.assertEqual("test description", Secret.objects.first().description)

        record = models.ChangeRecord.objects.create(
            change_set=self.change_set1,
            design_object=self.secret,
            full_control=False,
            changes={
                "description": {"old_value": "previous description", "new_value": "test description"},
            },
            index=self.change_set1._next_index(),  # pylint:disable=protected-access
        )
        record.validated_save()

        self.job.run(deployments=[self.deployment], delete=True)

        self.assertEqual(1, Secret.objects.count())
        self.assertEqual("previous description", Secret.objects.first().description)

    def test_decommission_run_without_full_control_dict_value_with_overlap(self):
        record = models.ChangeRecord.objects.create(
            change_set=self.change_set1,
            design_object=self.secret,
            full_control=False,
            changes={
                "parameters": {"old_value": self.initial_params, "new_value": self.changed_params},
            },
            index=self.change_set1._next_index(),  # pylint:disable=protected-access
        )
        record.validated_save()

        self.job.run(deployments=[self.deployment], delete=True)

        self.assertEqual(self.initial_params, Secret.objects.first().parameters)

    def test_decommission_run_without_full_control_dict_value_without_overlap(self):
        self.secret.parameters = {**self.initial_params, **self.changed_params}
        self.secret.validated_save()

        record = models.ChangeRecord.objects.create(
            change_set=self.change_set1,
            design_object=self.secret,
            full_control=False,
            changes={
                "parameters": {"old_value": self.initial_params, "new_value": self.changed_params},
            },
            index=self.change_set1._next_index(),  # pylint:disable=protected-access
        )
        record.validated_save()

        self.job.run(deployments=[self.deployment], delete=True)

        self.assertEqual(self.initial_params, Secret.objects.first().parameters)

    def test_decommission_run_without_full_control_dict_value_with_new_values_and_old_deleted(self):
        """Test complex dictionary decommission.

        This test validates that an original dictionary with `initial_params`, that gets added
        new values, and later another `new_value` out of control, and removing the `initial_params`
        works as expected.
        """
        record = models.ChangeRecord.objects.create(
            change_set=self.change_set1,
            design_object=self.secret,
            full_control=False,
            changes={
                "parameters": {"old_value": self.initial_params, "new_value": self.changed_params},
            },
            index=self.change_set1._next_index(),  # pylint:disable=protected-access
        )
        record.validated_save()

        # After the initial data, a new key value is added to the dictionary
        new_params = {"key3": "value3"}
        self.secret.parameters = {**self.changed_params, **new_params}
        self.secret.validated_save()

        self.job.run(deployments=[self.deployment], delete=True)

        self.assertEqual({**self.initial_params, **new_params}, Secret.objects.first().parameters)

    def test_decommission_run_with_pre_hook_pass(self):
        models.Deployment.pre_decommission.connect(fake_ok)
        self.assertEqual(1, Secret.objects.count())

        change_record_1 = models.ChangeRecord.objects.create(
            change_set=self.change_set1,
            design_object=self.secret,
            full_control=True,
            index=self.change_set1._next_index(),  # pylint:disable=protected-access
        )
        change_record_1.validated_save()

        self.job.run(deployments=[self.deployment], delete=True)

        self.assertEqual(0, Secret.objects.count())
        models.Deployment.pre_decommission.disconnect(fake_ok)

    def test_decommission_run_with_pre_hook_fail(self):
        models.Deployment.pre_decommission.connect(fake_ko)
        self.assertEqual(1, Secret.objects.count())
        change_record_1 = models.ChangeRecord.objects.create(
            change_set=self.change_set1,
            design_object=self.secret,
            full_control=True,
            index=self.change_set1._next_index(),  # pylint:disable=protected-access
        )
        change_record_1.validated_save()

        self.assertRaises(
            DesignValidationError,
            self.job.run,
            deployments=[self.deployment],
            delete=True,
        )

        self.assertEqual(1, Secret.objects.count())
        models.Deployment.pre_decommission.disconnect(fake_ko)

    def test_decommission_run_multiple_deployment(self):
        change_record = models.ChangeRecord.objects.create(
            change_set=self.change_set1,
            design_object=self.secret,
            full_control=True,
            index=self.change_set1._next_index(),  # pylint:disable=protected-access
        )
        change_record.validated_save()

        secret_2 = Secret.objects.create(
            name="test secret_2",
            provider="environment-variable",
            parameters=self.changed_params,
        )
        secret_2.validated_save()

        change_record_2 = models.ChangeRecord.objects.create(
            change_set=self.change_set2,
            design_object=secret_2,
            full_control=True,
            index=self.change_set2._next_index(),  # pylint:disable=protected-access
        )
        change_record_2.validated_save()

        self.assertEqual(2, Secret.objects.count())

        self.job.run(deployments=[self.deployment, self.deployment_2], delete=True)

        self.assertEqual(0, Secret.objects.count())

    def test_decommission_run_without_delete(self):
        self.assertEqual(1, Secret.objects.count())

        record = models.ChangeRecord.objects.create(
            change_set=self.change_set1,
            design_object=self.secret,
            full_control=True,
            index=self.change_set1._next_index(),  # pylint:disable=protected-access
        )
        record.validated_save()

        self.job.run(deployments=[self.deployment], delete=False)

        self.assertEqual(1, Secret.objects.count())
        record.refresh_from_db()
        self.assertEqual(False, record.active)
