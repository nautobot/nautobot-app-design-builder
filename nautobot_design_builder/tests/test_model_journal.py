"""Test Journal."""

from nautobot.dcim.models import Manufacturer

from .test_model_deployment import BaseDeploymentTest


class BaseJournalTest(BaseDeploymentTest):
    """Base Journal Test."""

    def setUp(self):
        super().setUp()
        self.original_name = "original equipment manufacturer"
        self.manufacturer = Manufacturer.objects.create(name=self.original_name)
        self.job_kwargs = {
            "manufacturer": f"{self.manufacturer.pk}",
            "instance": "my instance",
        }

        self.journal = self.create_journal(self.jobs[0], self.design_instance, self.job_kwargs)


class TestJournal(BaseJournalTest):
    """Test Journal."""

    def test_user_input(self):
        user_input = self.journal.user_input
        self.assertEqual(self.manufacturer, user_input["manufacturer"])
        self.assertEqual("my instance", user_input["instance"])
