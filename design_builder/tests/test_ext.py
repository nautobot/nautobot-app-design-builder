"""Unit tests related to template extensions."""
import sys

from django.test import TestCase

from design_builder.ext import DesignImplementationError
from design_builder.design import Builder
from design_builder import ext


class Extension(ext.Extension):
    """An extension for testing."""

    attribute_tag = "custom_extension"


class NotExtension:  # pylint: disable=too-few-public-methods
    """Something that is named an Extension but isn't an extension."""


class TestExtensionDiscovery(TestCase):
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
    def test_builder_called_with_custom_extensions(self):
        builder = Builder(extensions=[Extension])
        self.assertEqual(
            builder.extensions["attribute"]["custom_extension"]["class"],
            Extension,
        )

    def test_builder_called_with_invalid_extensions(self):
        self.assertRaises(DesignImplementationError, Builder, extensions=[NotExtension])
