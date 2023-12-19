"""Decommissioning Tests."""
from unittest import mock
import uuid


from django.contrib.contenttypes.models import ContentType
from django.test import override_settings


from nautobot.extras.models import JobResult
from nautobot.extras.models import Job as JobModel
from nautobot.extras.models import Status
from nautobot.extras.models import Secret
from nautobot_design_builder.tests import DesignTestCase

from nautobot_design_builder.util import nautobot_version
from nautobot_design_builder.jobs import DesignInstanceDecommissioning
from nautobot_design_builder import models, choices

from .designs import test_designs


def fake_ok(design_instance):  # pylint: disable=unused-argument
    """Fake function to return a pass for a hook."""
    return True, None


def fake_ko(design_instance):  # pylint: disable=unused-argument
    """Fake function to return a fail for a hook."""
    return False, "reason"


class DecommissionJobTestCase(DesignTestCase):  # pylint: disable=too-many-instance-attributes
    """Test the DecommissionJobTestCase class."""

    job_class = DesignInstanceDecommissioning

    def setUp(self):
        """Per-test setup."""
        super().setUp()

        # Decommissioning Job
        self.job = self.get_mocked_job(self.job_class)

        self.job.job_result = JobResult.objects.create(
            name="fake job",
            obj_type=ContentType.objects.get(app_label="extras", model="job"),
            job_id=uuid.uuid4(),
        )
        self.job.job_result.log = mock.Mock()

        # Design Builder Job
        defaults = {
            "grouping": "Designs",
            "source": "local",
            "installed": True,
            "module_name": test_designs.__name__.split(".")[-1],  # pylint: disable=use-maxsplit-arg
        }

        self.job1 = JobModel(
            **defaults.copy(),
            name="Simple Design",
            job_class_name=test_designs.SimpleDesign.__name__,
        )
        self.job1.validated_save()

        self.design1, _ = models.Design.objects.get_or_create(job=self.job1)
        self.content_type = ContentType.objects.get_for_model(models.DesignInstance)
        self.design_instance = models.DesignInstance(
            design=self.design1,
            name="My Design 1",
            status=Status.objects.get(content_types=self.content_type, name=choices.DesignInstanceStatusChoices.ACTIVE),
            live_state=Status.objects.get(
                content_types=self.content_type, name=choices.DesignInstanceLiveStateChoices.PENDING
            ),
        )
        self.design_instance.validated_save()

        self.design_instance_2 = models.DesignInstance(
            design=self.design1,
            name="My Design 2",
            status=Status.objects.get(content_types=self.content_type, name=choices.DesignInstanceStatusChoices.ACTIVE),
            live_state=Status.objects.get(
                content_types=self.content_type, name=choices.DesignInstanceLiveStateChoices.PENDING
            ),
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

        self.job_result = JobResult(
            job_model=self.job1,
            name=self.job1.class_path,
            job_id=uuid.uuid4(),
            obj_type=ContentType.objects.get_for_model(JobModel),
        )
        if nautobot_version < "2.0":
            self.job_result.job_kwargs = {"data": kwargs}
        else:
            self.job_result.task_kwargs = kwargs
        self.job_result.validated_save()

        self.journal1 = models.Journal(design_instance=self.design_instance, job_result=self.job_result)
        self.journal1.validated_save()

        self.journal2 = models.Journal(design_instance=self.design_instance_2, job_result=self.job_result)
        self.journal2.validated_save()

    def test_basic_decommission_run_with_full_control(self):
        self.assertEqual(1, Secret.objects.count())

        journal_entry = models.JournalEntry.objects.create(
            journal=self.journal1, design_object=self.secret, full_control=True
        )
        journal_entry.validated_save()

        self.job.run(data={"design_instances": [self.design_instance]}, commit=True)

        self.assertEqual(0, Secret.objects.count())

    def test_decommission_run_with_dependencies(self):
        self.assertEqual(1, Secret.objects.count())

        journal_entry_1 = models.JournalEntry.objects.create(
            journal=self.journal1, design_object=self.secret, full_control=True
        )

        journal_entry_1.validated_save()

        journal_entry_2 = models.JournalEntry.objects.create(
            journal=self.journal2, design_object=self.secret, full_control=False, changes={"differences": {}}
        )
        journal_entry_2.validated_save()

        # TODO: my refactoring caused this test to now fail. Need to
        # investigate.
        self.assertRaises(
            ValueError,
            self.job.run,
            {"design_instances": [self.design_instance]},
            True,
        )

        self.assertEqual(1, Secret.objects.count())

    def test_decommission_run_with_dependencies_but_decommissioned(self):
        self.assertEqual(1, Secret.objects.count())

        journal_entry_1 = models.JournalEntry.objects.create(
            journal=self.journal1, design_object=self.secret, full_control=True
        )

        journal_entry_1.validated_save()

        journal_entry_2 = models.JournalEntry.objects.create(
            journal=self.journal2, design_object=self.secret, full_control=False, changes={"differences": {}}
        )
        journal_entry_2.validated_save()

        self.design_instance_2.status = Status.objects.get(
            content_types=self.content_type, name=choices.DesignInstanceStatusChoices.DECOMMISSIONED
        )
        self.design_instance_2.validated_save()

        self.job.run(data={"design_instances": [self.design_instance]}, commit=True)

        self.assertEqual(0, Secret.objects.count())

    def test_basic_decommission_run_without_full_control(self):
        self.assertEqual(1, Secret.objects.count())

        journal_entry_1 = models.JournalEntry.objects.create(
            journal=self.journal1, design_object=self.secret, full_control=False, changes={"differences": {}}
        )
        journal_entry_1.validated_save()

        self.job.run(data={"design_instances": [self.design_instance]}, commit=True)

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
        )
        journal_entry.validated_save()

        self.job.run(data={"design_instances": [self.design_instance]}, commit=True)

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
        )
        journal_entry.validated_save()

        self.job.run(data={"design_instances": [self.design_instance]}, commit=True)

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
        )
        journal_entry.validated_save()

        self.job.run(data={"design_instances": [self.design_instance]}, commit=True)

        self.assertEqual(self.initial_params, Secret.objects.first().parameters)

    @override_settings(PLUGINS_CONFIG={"nautobot_design_builder": {"pre_decommission_hook": fake_ok}})
    def test_decommission_run_with_pre_hook_pass(self):
        self.assertEqual(1, Secret.objects.count())

        journal_entry_1 = models.JournalEntry.objects.create(
            journal=self.journal1, design_object=self.secret, full_control=True
        )
        journal_entry_1.validated_save()

        self.job.run(data={"design_instances": [self.design_instance]}, commit=True)

        self.assertEqual(0, Secret.objects.count())

    @override_settings(PLUGINS_CONFIG={"nautobot_design_builder": {"pre_decommission_hook": fake_ko}})
    def test_decommission_run_with_pre_hook_fail(self):
        self.assertEqual(1, Secret.objects.count())

        journal_entry_1 = models.JournalEntry.objects.create(
            journal=self.journal1, design_object=self.secret, full_control=True
        )
        journal_entry_1.validated_save()

        self.assertRaises(
            ValueError,
            self.job.run,
            {"design_instances": [self.design_instance]},
            True,
        )

        self.assertEqual(1, Secret.objects.count())

    def test_decommission_run_multiple_design_instance(self):
        journal_entry = models.JournalEntry.objects.create(
            journal=self.journal1, design_object=self.secret, full_control=True
        )
        journal_entry.validated_save()

        secret_2 = Secret.objects.create(
            name="test secret_2",
            provider="environment-variable",
            parameters=self.changed_params,
        )
        secret_2.validated_save()

        journal_entry_2 = models.JournalEntry.objects.create(
            journal=self.journal2, design_object=secret_2, full_control=True
        )
        journal_entry_2.validated_save()

        self.assertEqual(2, Secret.objects.count())

        self.job.run(data={"design_instances": [self.design_instance, self.design_instance_2]}, commit=True)

        self.assertEqual(0, Secret.objects.count())
