"""Decommissioning Tests."""

from unittest import mock

from django.contrib.contenttypes.models import ContentType

from nautobot.extras.models import JobResult
from nautobot.extras.models import Status
from nautobot.extras.models import Secret
from nautobot_design_builder.errors import DesignValidationError

from nautobot_design_builder.jobs import DeploymentDecommissioning
from nautobot_design_builder import models, choices
from nautobot_design_builder.tests.test_model_design import BaseDesignTest


def fake_ok(sender, design_instance, **kwargs):  # pylint: disable=unused-argument
    """Fake function to return a pass for a hook."""
    return True, None


def fake_ko(sender, design_instance, **kwargs):  # pylint: disable=unused-argument
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
        self.design_instance = models.Deployment(
            design=self.designs[0],
            name="My Design 1",
            status=Status.objects.get(content_types=self.content_type, name=choices.DeploymentStatusChoices.ACTIVE),
            version=self.design1.version,
        )
        self.design_instance.validated_save()

        self.design_instance_2 = models.Deployment(
            design=self.designs[0],
            name="My Design 2",
            status=Status.objects.get(content_types=self.content_type, name=choices.DeploymentStatusChoices.ACTIVE),
            version=self.design1.version,
        )
        self.design_instance_2.validated_save()

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

        self.job_result1 = JobResult(
            job_model=self.job1,
            name=self.job1.class_path,
            job_id=uuid.uuid4(),
            obj_type=ContentType.objects.get_for_model(JobModel),
        )
        self.job_result1.job_kwargs = {"data": kwargs}
        self.job_result1.validated_save()

        self.journal1 = models.Journal(design_instance=self.design_instance, job_result=self.job_result1)
        self.journal1.validated_save()

        self.job_result2 = JobResult.objects.create(
            job_model=self.jobs[0],
            name=self.jobs[0].class_path,
            task_kwargs=kwargs,
        )

        self.journal2 = models.Journal(design_instance=self.design_instance_2, job_result=self.job_result2)
        self.journal2.validated_save()

    def test_basic_decommission_run_with_full_control(self):
        self.assertEqual(1, Secret.objects.count())

        journal_entry = models.JournalEntry.objects.create(
            journal=self.journal1,
            design_object=self.secret,
            full_control=True,
            index=self.journal1._next_index(),  # pylint:disable=protected-access
        )
        journal_entry.validated_save()

        self.job.run(data={"deployments": [self.design_instance]})

        self.assertEqual(0, Secret.objects.count())

    def test_decommission_run_with_dependencies(self):
        self.assertEqual(1, Secret.objects.count())

        journal_entry_1 = models.JournalEntry.objects.create(
            journal=self.journal1,
            design_object=self.secret,
            full_control=True,
            index=self.journal1._next_index(),  # pylint:disable=protected-access
        )

        journal_entry_1.validated_save()

        journal_entry_2 = models.JournalEntry.objects.create(
            journal=self.journal2,
            design_object=self.secret,
            full_control=False,
            changes={
                "differences": {},
            },
            index=self.journal2._next_index(),  # pylint:disable=protected-access
        )
        journal_entry_2.validated_save()

        self.assertRaises(
            ValueError,
            self.job.run,
            {"deployments": [self.design_instance]},
        )

        self.assertEqual(1, Secret.objects.count())

    def test_decommission_run_with_dependencies_but_decommissioned(self):
        self.assertEqual(1, Secret.objects.count())

        journal_entry_1 = models.JournalEntry.objects.create(
            journal=self.journal1,
            design_object=self.secret,
            full_control=True,
            index=self.journal1._next_index(),  # pylint:disable=protected-access
        )

        journal_entry_1.validated_save()

        journal_entry_2 = models.JournalEntry.objects.create(
            journal=self.journal2,
            design_object=self.secret,
            full_control=False,
            changes={"differences": {}},
            index=self.journal2._next_index(),  # pylint:disable=protected-access
        )
        journal_entry_2.validated_save()

        self.design_instance_2.decommission()

        self.job.run(data={"deployments": [self.design_instance]})

        self.assertEqual(0, Secret.objects.count())

    def test_basic_decommission_run_without_full_control(self):
        self.assertEqual(1, Secret.objects.count())

        journal_entry_1 = models.JournalEntry.objects.create(
            journal=self.journal1,
            design_object=self.secret,
            full_control=False,
            changes={"differences": {}},
            index=self.journal1._next_index(),  # pylint:disable=protected-access
        )
        journal_entry_1.validated_save()

        self.job.run(data={"deployments": [self.design_instance]})

        self.assertEqual(1, Secret.objects.count())

    def test_decommission_run_without_full_control_string_value(self):
        self.assertEqual(1, Secret.objects.count())
        self.assertEqual("test description", Secret.objects.first().description)

        journal_entry = models.JournalEntry.objects.create(
            journal=self.journal1,
            design_object=self.secret,
            full_control=False,
            changes={
                "differences": {
                    "added": {"description": "test description"},
                    "removed": {"description": "previous description"},
                }
            },
            index=self.journal1._next_index(),  # pylint:disable=protected-access
        )
        journal_entry.validated_save()

        self.job.run(data={"deployments": [self.design_instance]})

        self.assertEqual(1, Secret.objects.count())
        self.assertEqual("previous description", Secret.objects.first().description)

    def test_decommission_run_without_full_control_dict_value_with_overlap(self):
        journal_entry = models.JournalEntry.objects.create(
            journal=self.journal1,
            design_object=self.secret,
            full_control=False,
            changes={
                "differences": {
                    "added": {"parameters": self.changed_params},
                    "removed": {"parameters": self.initial_params},
                }
            },
            index=self.journal1._next_index(),  # pylint:disable=protected-access
        )
        journal_entry.validated_save()

        self.job.run(data={"deployments": [self.design_instance]})

        self.assertEqual(self.initial_params, Secret.objects.first().parameters)

    def test_decommission_run_without_full_control_dict_value_without_overlap(self):
        self.secret.parameters = {**self.initial_params, **self.changed_params}
        self.secret.validated_save()

        journal_entry = models.JournalEntry.objects.create(
            journal=self.journal1,
            design_object=self.secret,
            full_control=False,
            changes={
                "differences": {
                    "added": {"parameters": self.changed_params},
                    "removed": {"parameters": self.initial_params},
                }
            },
            index=self.journal1._next_index(),  # pylint:disable=protected-access
        )
        journal_entry.validated_save()

        self.job.run(data={"deployments": [self.design_instance]})

        self.assertEqual(self.initial_params, Secret.objects.first().parameters)

    def test_decommission_run_without_full_control_dict_value_with_new_values_and_old_deleted(self):
        """Test complex dictionary decommission.

        This test validates that an original dictionary with `initial_params`, that gets added
        new values, and later another `new_value` out of control, and removing the `initial_params`
        works as expected.
        """
        journal_entry = models.JournalEntry.objects.create(
            journal=self.journal1,
            design_object=self.secret,
            full_control=False,
            changes={
                "differences": {
                    "added": {"parameters": self.changed_params},
                    "removed": {"parameters": self.initial_params},
                }
            },
            index=self.journal1._next_index(),  # pylint:disable=protected-access
        )
        journal_entry.validated_save()

        # After the initial data, a new key value is added to the dictionary
        new_params = {"key3": "value3"}
        self.secret.parameters = {**self.changed_params, **new_params}
        self.secret.validated_save()

        self.job.run(data={"deployments": [self.design_instance]})

        self.assertEqual({**self.initial_params, **new_params}, Secret.objects.first().parameters)

    def test_decommission_run_with_pre_hook_pass(self):
        models.Deployment.pre_decommission.connect(fake_ok)
        self.assertEqual(1, Secret.objects.count())

        journal_entry_1 = models.JournalEntry.objects.create(
            journal=self.journal1,
            design_object=self.secret,
            full_control=True,
            index=self.journal1._next_index(),  # pylint:disable=protected-access
        )
        journal_entry_1.validated_save()

        self.job.run(data={"deployments": [self.design_instance]})

        self.assertEqual(0, Secret.objects.count())
        models.Deployment.pre_decommission.disconnect(fake_ok)

    def test_decommission_run_with_pre_hook_fail(self):
        models.Deployment.pre_decommission.connect(fake_ko)
        self.assertEqual(1, Secret.objects.count())
        journal_entry_1 = models.JournalEntry.objects.create(
            journal=self.journal1,
            design_object=self.secret,
            full_control=True,
            index=self.journal1._next_index(),  # pylint:disable=protected-access
        )
        journal_entry_1.validated_save()

        self.assertRaises(
            DesignValidationError,
            self.job.run,
            {"deployments": [self.design_instance]},
        )

        self.assertEqual(1, Secret.objects.count())
        models.Deployment.pre_decommission.disconnect(fake_ko)

    def test_decommission_run_multiple_design_instance(self):
        journal_entry = models.JournalEntry.objects.create(
            journal=self.journal1,
            design_object=self.secret,
            full_control=True,
            index=self.journal1._next_index(),  # pylint:disable=protected-access
        )
        journal_entry.validated_save()

        secret_2 = Secret.objects.create(
            name="test secret_2",
            provider="environment-variable",
            parameters=self.changed_params,
        )
        secret_2.validated_save()

        journal_entry_2 = models.JournalEntry.objects.create(
            journal=self.journal2,
            design_object=secret_2,
            full_control=True,
            index=self.journal2._next_index(),  # pylint:disable=protected-access
        )
        journal_entry_2.validated_save()

        self.assertEqual(2, Secret.objects.count())

        self.job.run(data={"deployments": [self.design_instance, self.design_instance_2]})

        self.assertEqual(0, Secret.objects.count())
