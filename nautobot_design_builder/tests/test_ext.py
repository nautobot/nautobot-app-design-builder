"""Unit tests related to template extensions."""
import sys

from django.test import TestCase

from nautobot_design_builder import ext
from nautobot_design_builder.design import Builder
from nautobot_design_builder.ext import DesignImplementationError


class Extension(ext.AttributeExtension):
    """An extension for testing."""

    tag = "custom_extension"

    def attribute(self, value, model_instance) -> None:
        pass


class NotExtension:  # pylint: disable=too-few-public-methods
    """Something that is named an Extension but isn't an extension."""


class TestExtensionDiscovery(TestCase):
    """Test that extensions are discovered correctly."""

    def test_is_extension(self):
        self.assertTrue(ext.is_extension(Extension))
        self.assertFalse(ext.is_extension(NotExtension))

    def test_default_extensions(self):
        extensions = [ext.GitContextExtension, ext.ReferenceExtension]
        discovered_extensions = ext.extensions()
        for extension in extensions:
            self.assertIn(extension, discovered_extensions)

    def test_extensions(self):
        extensions = [Extension]
        discovered_extensions = ext.extensions(sys.modules[__name__])
        self.assertEqual(extensions, discovered_extensions)


class TestCustomExtensions(TestCase):
    """Test that custom extensions are loaded correctly."""

    def test_builder_called_with_custom_extensions(self):
        builder = Builder(extensions=[Extension])
        self.assertEqual(
            builder.extensions["attribute"]["custom_extension"]["class"],
            Extension,
        )

    def test_builder_called_with_invalid_extensions(self):
        self.assertRaises(DesignImplementationError, Builder, extensions=[NotExtension])


class TestExtensionCommitRollback(TestCase):
    """Test that extensions are called correctly."""

    @staticmethod
    def run_test(design, commit):
        """Implement a design and return wether or not `commit` and `roll_back` were called."""
        committed = False
        rolled_back = False

        class CommitExtension(ext.AttributeExtension):
            """Test extension."""

            tag = "extension"

            def attribute(self, value, model_instance) -> None:
                pass

            def commit(self) -> None:
                nonlocal committed
                committed = True

            def roll_back(self) -> None:
                nonlocal rolled_back
                rolled_back = True

        builder = Builder(extensions=[CommitExtension])
        try:
            builder.implement_design(design, commit=commit)
        except DesignImplementationError:
            pass
        return committed, rolled_back

    def test_extension_commit(self):
        design = {
            "manufacturers": [
                {
                    "name": "Test Manufacturer",
                    "!extension": True,
                }
            ]
        }
        committed, rolled_back = self.run_test(design, commit=True)
        self.assertTrue(committed)
        self.assertFalse(rolled_back)

    def test_extension_roll_back(self):
        design = {
            "manufacturers": [
                {
                    "!extension": True,
                    "name": "!ref:noref",
                }
            ]
        }
        committed, rolled_back = self.run_test(design, commit=True)
        self.assertTrue(rolled_back)
        self.assertFalse(committed)

    def test_extension_explicit_roll_back(self):
        design = {
            "manufacturers": [
                {
                    "name": "Test Manufacturer",
                    "!extension": True,
                }
            ]
        }
        committed, rolled_back = self.run_test(design, commit=False)
        self.assertTrue(rolled_back)
        self.assertFalse(committed)
