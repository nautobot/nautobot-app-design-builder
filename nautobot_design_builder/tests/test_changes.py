"""Tests for change utilities."""

from unittest import TestCase

from nautobot_design_builder.changes import revert_changed_dict


class TestRevertChangedDict(TestCase):
    """TestCase for the revert_changed_dict utility."""

    def test_added_key(self):
        original = {"key1": "initial-value"}
        changed = {"key1": "initial-value", "key2": "new-value"}
        current = {**changed}
        got = revert_changed_dict(current, original, changed)
        self.assertDictEqual(original, got)

    def test_extra_key(self):
        original = {"key1": "initial-value"}
        changed = {"key1": "initial-value", "key2": "new-value"}
        current = {"key1": "initial-value", "key2": "new-value", "key3": "key3-value"}
        got = revert_changed_dict(current, original, changed)
        self.assertDictEqual({"key1": "initial-value", "key3": "key3-value"}, got)

    def test_missing_changed_value_without_current(self):
        original = {"key1": "initial-value"}
        changed = {"key2": "new-value"}
        current = {"key2": "new-value", "key3": "key3-value"}
        got = revert_changed_dict(current, original, changed)
        self.assertDictEqual({"key1": "initial-value", "key3": "key3-value"}, got)

    def test_missing_changed_value_with_current(self):
        original = {"key1": "initial-value"}
        changed = {"key2": "new-value"}
        current = {"key1": "changed-value", "key2": "new-value", "key3": "key3-value"}
        got = revert_changed_dict(current, original, changed)
        self.assertDictEqual({"key1": "initial-value", "key3": "key3-value"}, got)
