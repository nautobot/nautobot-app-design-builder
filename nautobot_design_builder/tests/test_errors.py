"""Test design errors."""
import unittest

from django.core.exceptions import ValidationError

from nautobot_design_builder.errors import DesignModelError, DesignValidationError


class TestDesignModelError(unittest.TestCase):
    """Test DesignModelError."""

    class TestModel:  # pylint:disable=too-few-public-methods
        """A test model."""

        def __init__(self, title="", parent=None):
            self.title = title
            self.instance = self
            self.model_class = self
            self._meta = self
            self.verbose_name = "verbose name"
            self.parent = parent

        def __str__(self):
            return self.title

    def test_str_model(self):
        want = "Error Message"
        got = DesignModelError("Error Message").model_str
        self.assertEqual(want, got)

    def test_blank_instance_str(self):
        want = "Verbose name"
        got = DesignModelError(self.TestModel()).model_str
        self.assertEqual(want, got)

    def test_non_blank_instance_str(self):
        want = "Verbose name instance"
        got = DesignModelError(self.TestModel("instance")).model_str
        self.assertEqual(want, got)

    def test_path_str_no_parent(self):
        want = ("", "")
        got = DesignModelError(self.TestModel("instance")).path_str
        self.assertEqual(want, got)

    def test_path_str_one_parent(self):
        want = ("    ", "- Verbose name instance parent")
        parent = self.TestModel("instance parent")
        child = self.TestModel("instance child", parent=parent)
        got = DesignModelError(child).path_str
        self.assertEqual(want, got)

    def test_path_str_ancestors(self):
        want = ("        ", "- Verbose name instance grandparent\n    - Verbose name instance parent")
        grandparent = self.TestModel("instance grandparent")
        parent = self.TestModel("instance parent", parent=grandparent)
        child = self.TestModel("instance child", parent=parent)
        got = DesignModelError(child).path_str
        self.assertEqual(want, got)

    def test_explicit_parent(self):
        want = ("        ", "- Verbose name instance grandparent\n    - Verbose name instance parent")
        grandparent = self.TestModel("instance grandparent")
        parent = self.TestModel("instance parent", parent=grandparent)
        child = "instance child"
        got = DesignModelError(child, parent=parent).path_str
        self.assertEqual(want, got)


class TestDesignValidationError(unittest.TestCase):
    """Test DesignValidationError."""

    def test_single_string(self):
        want = "Error Message failed validation"
        got = str(DesignValidationError("Error Message"))
        self.assertEqual(want, got)

    def test_simple_validation_error(self):
        want = "Error Message failed validation\n\n  Secondary Message"
        got = DesignValidationError("Error Message")
        got.__cause__ = ValidationError("Secondary Message")
        self.assertEqual(want, str(got))

    def test_validation_error(self):
        want = "Model failed validation\n\n  **field1:** message1"
        got = DesignValidationError("Model")
        got.__cause__ = ValidationError({"field1": "message1"})
        self.assertEqual(want, str(got))

    def test_error_with_all_field(self):
        want = "Model failed validation\n\n  message1\n\n  **field1:** message2"
        got = DesignValidationError("Model")
        got.__cause__ = ValidationError({"__all__": "message1", "field1": "message2"})
        self.assertEqual(want, str(got))

        want = "Model failed validation\n\n  message2"
        got.__cause__ = ValidationError({"__all__": ValidationError(["message2"])})
        self.assertEqual(want, str(got))

    # TODO: need to add unit tests for model_stack logic
