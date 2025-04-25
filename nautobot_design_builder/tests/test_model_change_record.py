"""Test ChangeRecord."""

from unittest.mock import Mock, patch

from nautobot.dcim.models import DeviceType, Manufacturer
from nautobot.extras.models import Secret

from nautobot_design_builder.design import Environment
from nautobot_design_builder.errors import DesignValidationError

from ..models import ChangeRecord
from .test_model_deployment import BaseDeploymentTest


class TestChangeRecord(BaseDeploymentTest):  # pylint: disable=too-many-instance-attributes
    """Test ChangeRecord."""

    def setUp(self) -> None:
        super().setUp()
        # Used to test Scalars and Dictionaries
        self.secret = Secret.objects.create(
            name="test secret",
            provider="environment-variable",
            description="test description",
            parameters={"key1": "initial-value"},
        )

        # A ChangeRecord needs a ChangeSet
        self.original_name = "original equipment manufacturer"
        self.manufacturer = Manufacturer.objects.create(name=self.original_name)
        self.job_kwargs = {
            "manufacturer": f"{self.manufacturer.pk}",
            "instance": "my instance",
        }
        self.change_set = self.create_change_set(self.jobs[0], self.deployment, self.job_kwargs)

        self.initial_entry = ChangeRecord(
            design_object=self.secret,
            full_control=True,
            changes={
                "name": {"old_value": None, "new_value": "test secret"},
                "provider": {"old_value": None, "new_value": "environment-variable"},
                "description": {"old_value": None, "new_value": "test description"},
                "parameters": {"old_value": None, "new_value": {"key1": "initial-value"}},
            },
            change_set=self.change_set,
            index=0,
        )

        # Used to test Property attributes and ForeignKeys
        self.manufacturer = Manufacturer.objects.create(
            name="test manufacturer",
        )
        self.device_type = DeviceType.objects.create(model="test device type", manufacturer=self.manufacturer)

        self.initial_entry_device_type = ChangeRecord(
            design_object=self.device_type,
            full_control=True,
            changes={
                "model": {"old_value": None, "new_value": "test device type"},
                "manufacturer_id": {"old_value": None, "new_value": self.manufacturer.id},
            },
            change_set=self.change_set,
            index=1,
        )

    @patch("nautobot_design_builder.models.ChangeRecord.objects")
    def test_revert_full_control(self, objects: Mock):
        objects.filter_related.side_effect = lambda *args, **kwargs: objects
        objects.count.return_value = 0
        self.assertEqual(1, Secret.objects.count())
        self.initial_entry.revert()
        self.assertEqual(0, Secret.objects.count())

    @patch("nautobot_design_builder.models.ChangeRecord.objects")
    def test_revert_with_dependencies(self, objects: Mock):
        objects.filter_related.side_effect = lambda *args, **kwargs: objects
        objects.count.return_value = 1
        self.assertEqual(1, Secret.objects.count())
        self.assertRaises(DesignValidationError, self.initial_entry.revert)

    def test_updated_scalar(self):
        updated_secret = Secret.objects.get(id=self.secret.id)
        old_value = updated_secret.name
        updated_secret.name = "new name"
        updated_secret.save()
        entry = self.create_change_record(updated_secret, {"name": {"old_value": old_value, "new_value": "new name"}})
        entry.revert()
        self.secret.refresh_from_db()
        self.assertEqual(self.secret.name, "test secret")

    def test_add_dictionary_key(self):
        secret = Secret.objects.get(id=self.secret.id)
        old_value = {**secret.parameters}
        secret.parameters["key2"] = "new-value"
        secret.save()
        entry = self.create_change_record(
            secret, {"parameters": {"old_value": old_value, "new_value": secret.parameters}}
        )
        secret.refresh_from_db()
        self.assertDictEqual(
            secret.parameters,
            {
                "key1": "initial-value",
                "key2": "new-value",
            },
        )
        entry.revert()
        secret.refresh_from_db()
        self.assertDictEqual(
            secret.parameters,
            old_value,
        )

    def test_change_dictionary_key(self):
        secret = Secret.objects.get(id=self.secret.id)
        old_value = {**secret.parameters}
        secret.parameters["key1"] = "new-value"
        secret.save()
        entry = self.create_change_record(
            secret, {"parameters": {"old_value": old_value, "new_value": secret.parameters}}
        )
        secret.refresh_from_db()
        self.assertDictEqual(
            secret.parameters,
            {
                "key1": "new-value",
            },
        )
        entry.revert()
        secret.refresh_from_db()
        self.assertDictEqual(
            self.secret.parameters,
            old_value,
        )

    def test_remove_dictionary_key(self):
        secret = Secret.objects.get(id=self.secret.id)
        old_value = {**secret.parameters}
        secret.parameters = {"key2": "new-value"}
        secret.save()
        entry = self.create_change_record(
            secret, {"parameters": {"old_value": old_value, "new_value": secret.parameters}}
        )
        secret.refresh_from_db()
        self.assertDictEqual(
            secret.parameters,
            {
                "key2": "new-value",
            },
        )
        entry.revert()
        secret.refresh_from_db()
        self.assertDictEqual(
            self.secret.parameters,
            old_value,
        )

    def test_only_protected_field_attributes_are_reverted(self):
        """This test confirms that non-design dictionary keys are unaffected.

        Any Nautobot JSON field stored as an object (dictionary) is protected
        only for those object attributes (dictionary keys) that are part
        of the design. This means that keys added outside of the design process
        should remain when the design is reverted. This test confirms that
        behavior.
        """

        original_params = {"key1": "initial-value"}
        secret = Secret.objects.create(
            name="test secret 1",
            provider="environment-variable",
            description="test description",
            parameters=original_params,
        )
        secret.save()
        updated_params = {"key1": "initial-value", "key2": "changed-value"}
        environment = Environment()
        design_secret = environment.model_factory(Secret)(
            environment,
            {
                "!create_or_update:name": "test secret 1",
                "parameters": updated_params,
            },
        )
        design_secret.save()
        change_record = self.create_change_record(secret, design_secret.design_metadata.changes)
        secret.refresh_from_db()
        self.assertDictEqual(
            secret.parameters,
            updated_params,
        )

        # The "final params" is the design parameters "key2" plus a "key3" that
        # has been added outside of the design process.
        final_params = {"key2": "changed-value", "key3": "changed-value"}
        secret.parameters = final_params
        secret.save()
        change_record.revert()
        secret.refresh_from_db()
        # reverting should bring back key1 and leave key3 alone (since it was added outside of the
        # design process)
        self.assertDictEqual(secret.parameters, {"key1": "initial-value", "key3": "changed-value"})

    @patch("nautobot.extras.models.Secret.save")
    def test_reverting_without_old_value(self, save_mock: Mock):
        with patch("nautobot.extras.models.Secret.refresh_from_db"):
            secret = Secret(
                name="test secret 1",
                provider="environment-variable",
                description="Description",
                parameters=None,
            )
            secret.parameters = {"key1": "value1"}
            entry = self.create_change_record(secret, {"parameters": {"old_value": {}, "new_value": secret.parameters}})
            self.assertEqual(entry.design_object.parameters, {"key1": "value1"})
            entry.revert()
            self.assertEqual(entry.design_object.parameters, {})
            save_mock.assert_called()

    def test_change_foreign_key(self):
        new_manufacturer = Manufacturer.objects.create(name="new manufacturer")
        new_manufacturer.save()
        updated_device_type = DeviceType.objects.get(id=self.device_type.id)
        updated_device_type.manufacturer = new_manufacturer
        updated_device_type.save()

        entry = self.create_change_record(
            updated_device_type,
            {"manufacturer_id": {"old_value": self.manufacturer.id, "new_value": new_manufacturer.id}},
        )
        entry.revert()
        self.device_type.refresh_from_db()
        self.assertEqual(self.device_type.manufacturer, self.manufacturer)
