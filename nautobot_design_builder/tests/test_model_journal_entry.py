"""Test Journal."""

from unittest.mock import patch, Mock
from nautobot.extras.models import Secret
from nautobot.dcim.models import Manufacturer, DeviceType
from nautobot.apps.models import serialize_object_v2

from nautobot_design_builder.design import calculate_changes
from nautobot_design_builder.errors import DesignValidationError

from .test_model_design_instance import BaseDesignInstanceTest
from ..models import JournalEntry


class TestJournalEntry(BaseDesignInstanceTest):  # pylint: disable=too-many-instance-attributes
    """Test JournalEntry."""

    def setUp(self) -> None:
        super().setUp()
        # Used to test Scalars and Dictionaries
        self.secret = Secret.objects.create(
            name="test secret",
            provider="environment-variable",
            description="test description",
            parameters={"key1": "initial-value"},
        )
        self.initial_state = serialize_object_v2(self.secret)

        # A JournalEntry needs a Journal
        self.original_name = "original equipment manufacturer"
        self.manufacturer = Manufacturer.objects.create(name=self.original_name)
        self.job_kwargs = {
            "manufacturer": f"{self.manufacturer.pk}",
            "instance": "my instance",
        }
        self.journal = self.create_journal(self.jobs[0], self.design_instance, self.job_kwargs)

        self.initial_entry = JournalEntry(
            design_object=self.secret,
            full_control=True,
            changes=calculate_changes(self.secret),
            journal=self.journal,
            index=0,
        )

        # Used to test Property attributes and ForeignKeys
        self.manufacturer = Manufacturer.objects.create(
            name="test manufacturer",
        )
        self.device_type = DeviceType.objects.create(model="test device type", manufacturer=self.manufacturer)

        self.initial_state_device_type = serialize_object_v2(self.device_type)
        self.initial_entry_device_type = JournalEntry(
            design_object=self.device_type,
            full_control=True,
            changes=calculate_changes(self.device_type),
            journal=self.journal,
            index=1,
        )

    def get_entry(self, updated_object, design_object=None, initial_state=None):
        """Generate a JournalEntry."""
        if design_object is None:
            design_object = self.secret

        if initial_state is None:
            initial_state = self.initial_state

        return JournalEntry(
            design_object=design_object,
            changes=calculate_changes(
                updated_object,
                initial_state=initial_state,
            ),
            full_control=False,
            journal=self.journal,
            index=self.journal._next_index(),  # pylint:disable=protected-access
        )

    @patch("nautobot_design_builder.models.JournalEntry.objects")
    def test_revert_full_control(self, objects: Mock):
        objects.filter_related.side_effect = lambda *args, **kwargs: objects
        objects.values_list.side_effect = lambda *args, **kwargs: []
        self.assertEqual(1, Secret.objects.count())
        self.initial_entry.revert()
        self.assertEqual(0, Secret.objects.count())

    @patch("nautobot_design_builder.models.JournalEntry.objects")
    def test_revert_with_dependencies(self, objects: Mock):
        objects.filter_related.side_effect = lambda *args, **kwargs: objects
        objects.values_list.side_effect = lambda *args, **kwargs: [12345]
        self.assertEqual(1, Secret.objects.count())
        self.assertRaises(DesignValidationError, self.initial_entry.revert)

    def test_updated_scalar(self):
        updated_secret = Secret.objects.get(id=self.secret.id)
        updated_secret.name = "new name"
        updated_secret.save()
        entry = self.get_entry(updated_secret)
        entry.revert()
        self.secret.refresh_from_db()
        self.assertEqual(self.secret.name, "test secret")

    def test_add_dictionary_key(self):
        secret = Secret.objects.get(id=self.secret.id)
        secret.parameters["key2"] = "new-value"
        secret.save()
        entry = self.get_entry(secret)
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
            {
                "key1": "initial-value",
            },
        )

    def test_change_dictionary_key(self):
        secret = Secret.objects.get(id=self.secret.id)
        secret.parameters["key1"] = "new-value"
        secret.save()
        entry = self.get_entry(secret)
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
            {
                "key1": "initial-value",
            },
        )

    def test_remove_dictionary_key(self):
        secret = Secret.objects.get(id=self.secret.id)
        secret.parameters = {"key2": "new-value"}
        secret.save()
        entry = self.get_entry(secret)
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
            {
                "key1": "initial-value",
            },
        )

    def test_new_key_reverted_without_original_and_with_a_new_one(self):
        secret = Secret.objects.get(id=self.secret.id)
        secret.parameters["key2"] = "changed-value"
        secret.save()
        secret.refresh_from_db()
        self.assertDictEqual(
            secret.parameters,
            {"key1": "initial-value", "key2": "changed-value"},
        )

        # Delete the initial value and add a new one
        del secret.parameters["key1"]
        secret.parameters["key3"] = "changed-value"
        secret.save()
        self.assertDictEqual(
            secret.parameters,
            {
                "key2": "changed-value",
                "key3": "changed-value",
            },
        )

        entry = self.get_entry(secret)
        entry.revert()
        secret.refresh_from_db()
        self.assertDictEqual(self.secret.parameters, secret.parameters)

    @patch("nautobot.extras.models.Secret.save")
    def test_reverting_without_old_value(self, save_mock: Mock):
        with patch("nautobot.extras.models.Secret.refresh_from_db"):
            secret = Secret(
                name="test secret 1",
                provider="environment-variable",
                description="Description",
                parameters=None,
            )
            initial_state = serialize_object_v2(secret)
            secret.parameters = {"key1": "value1"}
            entry = self.get_entry(secret, secret, initial_state)
            self.assertEqual(entry.design_object.parameters, {"key1": "value1"})
            entry.revert()
            self.assertEqual(entry.design_object.parameters, {})
            save_mock.assert_called()

    @patch("nautobot.extras.models.Secret.save")
    def test_reverting_without_new_value(self, save_mock: Mock):
        with patch("nautobot.extras.models.Secret.refresh_from_db"):
            secret = Secret(
                name="test secret 1",
                provider="environment-variable",
                description="Description",
                parameters={"key1": "value1"},
            )
            initial_state = serialize_object_v2(secret)
            secret.parameters = None
            entry = self.get_entry(secret, secret, initial_state)
            self.assertEqual(entry.design_object.parameters, None)
            entry.revert()
            self.assertEqual(entry.design_object.parameters, {"key1": "value1"})
            save_mock.assert_called()

    def test_change_property(self):
        """This test checks that the 'display' property is properly managed."""
        updated_device_type = DeviceType.objects.get(id=self.device_type.id)
        updated_device_type.model = "new name"
        updated_device_type.save()
        entry = self.get_entry(
            updated_device_type, design_object=self.device_type, initial_state=self.initial_state_device_type
        )
        entry.revert()
        self.device_type.refresh_from_db()
        self.assertEqual(self.device_type.model, "test device type")

    def test_change_foreign_key(self):
        new_manufacturer = Manufacturer.objects.create(name="new manufacturer")
        new_manufacturer.save()
        updated_device_type = DeviceType.objects.get(id=self.device_type.id)
        updated_device_type.manufacturer = new_manufacturer
        updated_device_type.save()

        entry = self.get_entry(
            updated_device_type, design_object=self.device_type, initial_state=self.initial_state_device_type
        )
        entry.revert()
        self.device_type.refresh_from_db()
        self.assertEqual(self.device_type.manufacturer, self.manufacturer)
