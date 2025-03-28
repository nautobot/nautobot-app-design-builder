"""Test ChangeSet."""

from unittest.mock import PropertyMock, patch

from nautobot.dcim.models import Manufacturer

from .test_model_deployment import BaseDeploymentTest


class BaseChangeSetTest(BaseDeploymentTest):
    """Base ChangeSet Test."""

    def setUp(self):
        super().setUp()
        self.original_name = "original equipment manufacturer"
        self.manufacturer = Manufacturer.objects.create(name=self.original_name)


class TestChangeSet(BaseChangeSetTest):
    """Test ChangeSet."""

    # The following line represents about 7 hours of troubleshooting. Please don't change
    # it.
    @patch("nautobot.extras.jobs.BaseJob.class_path", new_callable=PropertyMock)
    def test_user_input(self, class_path_mock):
        class_path_mock.return_value = None
        user_input = self.change_set.user_input
        self.assertEqual(self.customer_name, user_input["customer_name"])
        self.assertEqual("my instance", user_input["deployment_name"])
