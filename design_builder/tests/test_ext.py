"""Unit tests related to template extensions."""
import sys
import yaml

from django.db.models import Q
from django.test import TestCase

from nautobot.extras.models import Status
from nautobot.dcim.models import Interface, DeviceType
from nautobot.tenancy.models import Tenant
from nautobot.ipam.models import Prefix

from design_builder import ext
from design_builder.contrib.ext import LookupExtension, CableConnectionExtension, NextPrefixExtension
from design_builder.design import Builder
from design_builder.ext import DesignImplementationError
from design_builder.util import nautobot_version


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
        manufacturers:
            - name: "Manufacturer"

        device_types:
            - "!lookup:manufacturer":
                name: "Manufacturer"
              model: "model"
        """
        design = yaml.safe_load(design_template)
        builder = Builder(extensions=[LookupExtension])
        builder.implement_design(design, commit=True)
        device_type = DeviceType.objects.get(model="model")
        self.assertEqual("Manufacturer", device_type.manufacturer.name)

    def test_lookup_by_single_attribute(self):
        design_template = """
        manufacturers:
            - name: "Manufacturer"

        device_types:
            - "!lookup:manufacturer:name": "Manufacturer"
              model: "model"
        """
        design = yaml.safe_load(design_template)
        builder = Builder(extensions=[LookupExtension])
        builder.implement_design(design, commit=True)
        device_type = DeviceType.objects.get(model="model")
        self.assertEqual("Manufacturer", device_type.manufacturer.name)


class TestCableConnectionExtension(TestCase):
    def test_connect_cable(self):
        design_template_v1 = """
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

        design_template_v2 = """
        location_types:
          - name: "Site"
            content_types:
                - "!get:app_label": "dcim"
                  "!get:model": "device"
        locations:
          - location_type__name: "Site"
            name: "Site"
            status__name: "Active"
        roles:
          - name: "test-role"
            content_types:
                - "!get:app_label": "dcim"
                  "!get:model": "device"
        manufacturers:
          - name: "test-manufacturer"
        device_types:
          - manufacturer__name: "test-manufacturer"
            model: "test-type"
        devices:
            - name: "Device 1"
              "!ref": "device1"
              location__name: "Site"
              status__name: "Active"
              role__name: "test-role"
              device_type__model: "test-type"
              interfaces:
                - name: "GigabitEthernet1"
                  type: "1000base-t"
                  status__name: "Active"
            - name: "Device 2"
              location__name: "Site"
              status__name: "Active"
              role__name: "test-role"
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

        if nautobot_version < "2.0.0":
            design = yaml.safe_load(design_template_v1)
        else:
            design = yaml.safe_load(design_template_v2)

        builder = Builder(extensions=[CableConnectionExtension])
        builder.implement_design(design, commit=True)
        interfaces = Interface.objects.all()
        self.assertEqual(2, len(interfaces))
        self.assertEqual(interfaces[0].connected_endpoint, interfaces[1])


def create_prefix(prefix, **kwargs):  # pylint:disable=missing-function-docstring
    prefix, _ = Prefix.objects.get_or_create(
        prefix=prefix,
        defaults={
            "status": Status.objects.get(name="Active"),
            **kwargs,
        },
    )
    return prefix


class TestNextPrefixExtension(TestCase):
    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(name="Nautobot Airports")
        if nautobot_version < "2.0.0":
            from nautobot.ipam.models import Role  # pylint: disable=no-name-in-module,import-outside-toplevel
        else:
            from nautobot.extras.models import Role  # pylint: disable=no-name-in-module,import-outside-toplevel

        self.server_role = Role.objects.create(name="servers")
        self.video_role = Role.objects.create(name="video")
        self.prefixes = []
        self.prefixes.append(create_prefix("10.0.0.0/8", tenant=self.tenant))
        self.prefixes.append(create_prefix("10.0.0.0/23", tenant=self.tenant, role=self.server_role))
        self.prefixes.append(create_prefix("10.0.2.0/23", tenant=self.tenant, role=self.video_role))

    def test_next_prefix_lookup(self):
        extension = NextPrefixExtension(None)
        want = "10.0.4.0/24"
        got = extension._get_next([self.prefixes[0]], "24")  # pylint:disable=protected-access
        self.assertEqual(want, got)

    def test_next_prefix_lookup_from_full_prefix(self):
        for prefix in ["10.0.0.0/24", "10.0.1.0/24"]:
            create_prefix(prefix)

        prefixes = Prefix.objects.filter(
            Q(network="10.0.0.0", prefix_length=23) | Q(network="10.0.2.0", prefix_length=23)
        )

        extension = NextPrefixExtension(None)
        want = "10.0.2.0/24"
        got = extension._get_next(prefixes, "24")  # pylint:disable=protected-access
        self.assertEqual(want, got)

    def test_creation(self):
        design_template = """
        prefixes:
            - "!next_prefix":
                prefix:
                - "10.0.0.0/23"
                - "10.0.2.0/23"
                length: 24
              status__name: "Active"
            - "!next_prefix":
                prefix:
                - "10.0.0.0/23"
                - "10.0.2.0/23"
                length: 24
              status__name: "Active"
            - "!next_prefix":
                prefix:
                - "10.0.0.0/23"
                - "10.0.2.0/23"
                length: 24
              status__name: "Active"
            - "!next_prefix":
                prefix:
                - "10.0.0.0/23"
                - "10.0.2.0/23"
                length: 24
              status__name: "Active"
        """
        design = yaml.safe_load(design_template)
        object_creator = Builder(extensions=[NextPrefixExtension])
        object_creator.implement_design(design, commit=True)
        self.assertTrue(Prefix.objects.filter(prefix="10.0.0.0/24").exists())
        self.assertTrue(Prefix.objects.filter(prefix="10.0.1.0/24").exists())
        self.assertTrue(Prefix.objects.filter(prefix="10.0.2.0/24").exists())
        self.assertTrue(Prefix.objects.filter(prefix="10.0.3.0/24").exists())

    def test_lookup_by_role_and_tenant(self):
        design_template = """
        prefixes:
            - "!next_prefix":
                role__name: "video"
                tenant__name: "Nautobot Airports"
                length: 24
              status__name: "Active"
        """
        self.assertFalse(Prefix.objects.filter(prefix="10.0.2.0/24").exists())
        design = yaml.safe_load(design_template)
        object_creator = Builder(extensions=[NextPrefixExtension])
        object_creator.implement_design(design, commit=True)
        self.assertTrue(Prefix.objects.filter(prefix="10.0.2.0/24").exists())
