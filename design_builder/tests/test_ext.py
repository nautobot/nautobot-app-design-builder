"""Unit tests related to template extensions."""
import sys
import yaml

from django.test import TestCase

from nautobot.dcim.models import Site, Interface

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


class TestLookupExtension(TestCase):
    def test_lookup_by_dict(self):
        design_template = """
        sites:
            - name: "Site"
              "!lookup:status":
                name: "Active"
        """
        design = yaml.safe_load(design_template)
        builder = Builder()
        builder.implement_design(design, commit=True)
        site = Site.objects.get(name="Site")
        self.assertEqual("Active", site.status.name)

    def test_lookup_by_single_attribute(self):
        design_template = """
        sites:
            - name: "Site"
              "!lookup:status:name": "Active"
        """
        design = yaml.safe_load(design_template)
        builder = Builder()
        builder.implement_design(design, commit=True)
        site = Site.objects.get(name="Site")
        self.assertEqual("Active", site.status.name)


class TestCableConnectionExtension(TestCase):
    def test_connect_cable(self):
        design_template = """
        sites:
          - name: "Site"
            status__name: "Active"
        device_roles:
          - name: "test-role"
        manufacturers:
          - name: "test-manufacturer"
        device_types:
          - manufacturer__name: "test-manufacturer"
            model: "test-type"
        devices:
            - name: "Device 1"
              "!ref": "device1"
              site__name: "Site"
              status__name: "Active"
              device_role__name: "test-role"
              device_type__model: "test-type"
              interfaces:
                - name: "GigabitEthernet1"
                  type: "1000base-t"
                  status__name: "Active"
            - name: "Device 2"
              site__name: "Site"
              status__name: "Active"
              device_role__name: "test-role"
              device_type__model: "test-type"
              interfaces:
                - name: "GigabitEthernet1"
                  type: "1000base-t"
                  status__name: "Active"
                  "!connect_cable":
                    status__name: "Planned"
                    device: "!ref:device1"
                    name: "GigabitEthernet1"
        """
        design = yaml.safe_load(design_template)
        builder = Builder()
        builder.implement_design(design, commit=True)
        interfaces = Interface.objects.all()
        self.assertEqual(2, len(interfaces))
        self.assertEqual(interfaces[0].connected_endpoint, interfaces[1])
