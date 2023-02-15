"""Test design errors."""
import unittest

from django.core.exceptions import ValidationError

from design_builder.errors import DesignValidationError


class TestDesignValidationError(unittest.TestCase):
    def test_single_string(self):
        want = "Error Message"
        got = str(DesignValidationError(want))
        self.assertEqual(want, got)

    def test_simple_validation_error(self):
        want = "Error Message\n\nSecondary Message"
        got = DesignValidationError("Error Message")
        got.__cause__ = ValidationError("Secondary Message")
        self.assertEqual(want, str(got))

    def test_validation_error(self):
        want = "Error Message\n\n**field1:** message1"
        got = DesignValidationError("Error Message")
        got.__cause__ = ValidationError({"field1": "message1"})
        self.assertEqual(want, str(got))

    def test_error_with_all_field(self):
        want = "Error Message\n\nmessage1\n\n**field1:** message2"
        got = DesignValidationError("Error Message")
        got.__cause__ = ValidationError({"__all__": "message1", "field1": "message2"})
        self.assertEqual(want, str(got))

        want = "Error Message\n\nmessage2"
        got.__cause__ = ValidationError({"__all__": ValidationError(["message2"])})
        self.assertEqual(want, str(got))
