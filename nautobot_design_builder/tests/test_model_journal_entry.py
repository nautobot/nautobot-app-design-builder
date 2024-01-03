"""Test Journal."""
from unittest.mock import patch, Mock
from django.core.exceptions import ValidationError
from django.test import TestCase
from nautobot.extras.models import Secret
from nautobot.utilities.utils import serialize_object_v2

from nautobot_design_builder.design import calculate_changes

from ..models import JournalEntry


class TestJournalEntry(TestCase):
    """Test JournalEntry."""

    def setUp(self) -> None:
        super().setUp()
        self.secret = Secret.objects.create(
            name="test secret",
            provider="environment-variable",
            description="test description",
            parameters={"key1": "initial-value"},
        )
        self.initial_state = serialize_object_v2(self.secret)
        self.initial_entry = JournalEntry(
            design_object=self.secret,
            full_control=True,
            changes=calculate_changes(self.secret),
        )

    def get_entry(self, updated_secret, design_object=None, initial_state=None):
        """Generate a JournalEntry."""
        if design_object is None:
            design_object = self.secret

        if initial_state is None:
            initial_state = self.initial_state

        return JournalEntry(
            design_object=design_object,
            changes=calculate_changes(
                updated_secret,
                initial_state=initial_state,
            ),
        )

    @patch("nautobot_design_builder.models.JournalEntry.objects")
    def test_revert_full_control(self, objects: Mock):
        objects.filter_related.side_effect = lambda _: objects
        objects.exclude_decommissioned.return_value = []
        self.assertEqual(1, Secret.objects.count())
        self.initial_entry.revert()
        objects.filter_related.assert_called()
        objects.exclude_decommissioned.assert_called()
        self.assertEqual(0, Secret.objects.count())

    @patch("nautobot_design_builder.models.JournalEntry.objects")
    def test_revert_with_dependencies(self, objects: Mock):
        objects.filter_related.side_effect = lambda _: objects
        self.assertEqual(1, Secret.objects.count())
        entry2 = JournalEntry()
        objects.exclude_decommissioned.return_value = [entry2]
        self.assertRaises(ValidationError, self.initial_entry.revert)
        objects.exclude_decommissioned.assert_called()

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
            self.assertEqual(entry.design_object.parameters, None)
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
