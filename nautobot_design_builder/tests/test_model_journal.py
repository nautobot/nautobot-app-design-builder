"""Test Journal."""

from nautobot.dcim.models import Manufacturer

from .test_model_deployment import BaseDeploymentTest


class BaseJournalTest(BaseDeploymentTest):
    """Base Journal Test."""

    def setUp(self):
        super().setUp()
        self.original_name = "original equipment manufacturer"
        self.customer_name = "Customer 1"
        self.job_kwargs = {
            "customer_name": self.customer_name,
            "deployment_name": "my instance",
        }

        self.journal = self.create_journal(self.job, self.deployment, self.job_kwargs)


class TestJournal(BaseJournalTest):
    """Test Journal."""

    def test_user_input(self):
        user_input = self.journal.user_input
        self.assertEqual(self.customer_name, user_input["customer_name"])
        self.assertEqual("my instance", user_input["deployment_name"])
