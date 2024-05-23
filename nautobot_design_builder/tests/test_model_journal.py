"""Test Journal."""

from unittest.mock import patch, PropertyMock

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

    # The following line represents about 7 hours of troubleshooting. Please don't change
    # it.
    @patch("nautobot.extras.jobs.BaseJob.class_path", new_callable=PropertyMock)
    def test_user_input(self, class_path_mock):
        class_path_mock.return_value = None
        user_input = self.journal.user_input
        self.assertEqual(self.customer_name, user_input["customer_name"])
        self.assertEqual("my instance", user_input["deployment_name"])
