"""Unit tests related to template extensions."""
import yaml

from django.db.models import Q
from django.test import TestCase

from nautobot.extras.models import Status
from nautobot.dcim.models import Interface, Device, DeviceType
from nautobot.tenancy.models import Tenant
from nautobot.ipam.models import Prefix

from nautobot_design_builder.contrib.ext import (
    BGPPeeringExtension,
    ChildPrefixExtension,
    LookupExtension,
    CableConnectionExtension,
    NextPrefixExtension,
)
from nautobot_design_builder.design import Builder
from nautobot_design_builder.util import nautobot_version


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
          - "!create_or_update:name": "Site"
            status__name: "Active"
        device_roles:
          - "!create_or_update:name": "test-role"
        manufacturers:
          - "!create_or_update:name": "test-manufacturer"
        device_types:
          - manufacturer__name: "test-manufacturer"
            "!create_or_update:model": "test-type"
        devices:
            - "!create_or_update:name": "Device 1"
              "!ref": "device1"
              site__name: "Site"
              status__name: "Active"
              device_role__name: "test-role"
              device_type__model: "test-type"
              interfaces:
                - "!create_or_update:name": "GigabitEthernet1"
                  type: "1000base-t"
                  status__name: "Active"
            - "!create_or_update:name": "Device 2"
              site__name: "Site"
              status__name: "Active"
              device_role__name: "test-role"
              device_type__model: "test-type"
              interfaces:
                - "!create_or_update:name": "GigabitEthernet1"
                  type: "1000base-t"
                  status__name: "Active"
                  "!connect_cable":
                    status__name: "Planned"
                    to:
                      device: "!ref:device1"
                      name: "GigabitEthernet1"
        """

        design_template_v2 = """
        location_types:
          - "!create_or_update:name": "Site"
            content_types:
                - "!get:app_label": "dcim"
                  "!get:model": "device"
        locations:
          - location_type__name: "Site"
            "!create_or_update:name": "Site"
            status__name: "Active"
        roles:
          - "!create_or_update:name": "test-role"
            content_types:
                - "!get:app_label": "dcim"
                  "!get:model": "device"
        manufacturers:
          - "!create_or_update:name": "test-manufacturer"
        device_types:
          - manufacturer__name: "test-manufacturer"
            "!create_or_update:model": "test-type"
        devices:
            - "!create_or_update:name": "Device 1"
              "!ref": "device1"
              location__name: "Site"
              status__name: "Active"
              role__name: "test-role"
              device_type__model: "test-type"
              interfaces:
                - "!create_or_update:name": "GigabitEthernet1"
                  type: "1000base-t"
                  status__name: "Active"
            - "!create_or_update:name": "Device 2"
              location__name: "Site"
              status__name: "Active"
              role__name: "test-role"
              device_type__model: "test-type"
              interfaces:
                - "!create_or_update:name": "GigabitEthernet1"
                  type: "1000base-t"
                  status__name: "Active"
                  "!connect_cable":
                    status__name: "Planned"
                    to:
                      device: "!ref:device1"
                      name: "GigabitEthernet1"
        """

        if nautobot_version < "2.0.0":
            design = yaml.safe_load(design_template_v1)
        else:
            design = yaml.safe_load(design_template_v2)

        # test idempotence by running it twice:
        for _ in range(2):
            builder = Builder(extensions=[CableConnectionExtension])
            builder.implement_design(design, commit=True)
            interfaces = Interface.objects.all()
            self.assertEqual(2, len(interfaces))
            self.assertEqual(interfaces[0].connected_endpoint, interfaces[1])
            self.assertIsNotNone(interfaces[0]._path_id)  # pylint: disable=protected-access
            self.assertIsNotNone(interfaces[1]._path_id)  # pylint: disable=protected-access


class PrefixExtensionTests(TestCase):
    """Base class for testing prefix based extensions."""

    @staticmethod
    def create_prefix(prefix, **kwargs):
        """Affirm the existence of a prefix and return it."""
        prefix, _ = Prefix.objects.get_or_create(
            prefix=prefix,
            defaults={
                "status": Status.objects.get(name="Active"),
                **kwargs,
            },
        )
        return prefix

    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(name="Nautobot Airports")
        if nautobot_version < "2.0.0":
            from nautobot.ipam.models import Role  # pylint: disable=no-name-in-module,import-outside-toplevel
        else:
            from nautobot.extras.models import Role  # pylint: disable=no-name-in-module,import-outside-toplevel

        self.server_role = Role.objects.create(name="servers")
        self.video_role = Role.objects.create(name="video")
        self.prefixes = []
        self.prefixes.append(PrefixExtensionTests.create_prefix("10.0.0.0/8", tenant=self.tenant))
        self.prefixes.append(
            PrefixExtensionTests.create_prefix("10.0.0.0/23", tenant=self.tenant, role=self.server_role)
        )
        self.prefixes.append(
            PrefixExtensionTests.create_prefix("10.0.2.0/23", tenant=self.tenant, role=self.video_role)
        )


class TestNextPrefixExtension(PrefixExtensionTests):
    def test_next_prefix_lookup(self):
        extension = NextPrefixExtension(None)
        want = "10.0.4.0/24"
        got = extension._get_next([self.prefixes[0]], "24")  # pylint:disable=protected-access
        self.assertEqual(want, got)

    def test_next_prefix_lookup_from_full_prefix(self):
        for prefix in ["10.0.0.0/24", "10.0.1.0/24"]:
            PrefixExtensionTests.create_prefix(prefix)

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


class TestChildPrefixExtension(PrefixExtensionTests):
    def test_creation(self):
        design_template = """
        prefixes:
            - "!next_prefix":
                prefix:
                - "10.0.0.0/23"
                length: 24
              status__name: "Active"
              "!ref": "parent_prefix"
            - "!child_prefix":
                parent: "!ref:parent_prefix"
                offset: "0.0.0.0/25"
              status__name: "Active"
            - "!child_prefix":
                parent: "!ref:parent_prefix"
                offset: "0.0.0.128/25"
              status__name: "Active"
        """
        design = yaml.safe_load(design_template)
        object_creator = Builder(extensions=[NextPrefixExtension, ChildPrefixExtension])
        object_creator.implement_design(design, commit=True)
        self.assertTrue(Prefix.objects.filter(prefix="10.0.0.0/24").exists())
        self.assertTrue(Prefix.objects.filter(prefix="10.0.0.0/25").exists())
        self.assertTrue(Prefix.objects.filter(prefix="10.0.0.128/25").exists())


class TestBGPExtension(TestCase):
    def setUp(self):
        # TODO: Remove this when BGP models is migrated to 2.0
        if nautobot_version >= "2.0.0":
            self.skipTest("BGP Models is not supported in Nautobot 2.x")
        super().setUp()

    def test_creation(self):
        design_template = """
        sites:
          - "!create_or_update:name": "Site"
            status__name: "Active"

        device_roles:
          - "!create_or_update:name": "test-role"

        manufacturers:
          - "!create_or_update:name": "test-manufacturer"

        device_types:
          - manufacturer__name: "test-manufacturer"
            "!create_or_update:model": "test-type"

        autonomous_systems:
        - "!create_or_update:asn": 64500
          status__name: "Active"

        devices:
        - "!create_or_update:name": "device1"
          status__name: "Active"
          site__name: "Site"
          device_role__name: "test-role"
          device_type__model: "test-type"
          interfaces:
          - "!create_or_update:name": "Ethernet1/1"
            type: "virtual"
            status__name: "Active"
            ip_addresses:
            - "!create_or_update:address": "192.168.1.1/24"
              status__name: "Active"
          bgp_routing_instances:
          - "!create_or_update:autonomous_system__asn": 64500
            "!ref": "device1-instance"

        - "!create_or_update:name": "device2"
          status__name: "Active"
          site__name: "Site"
          device_role__name: "test-role"
          device_type__model: "test-type"
          interfaces:
          - "!create_or_update:name": "Ethernet1/1"
            type: "virtual"
            status__name: "Active"
            ip_addresses:
            - "!create_or_update:address": "192.168.1.2/24"
              status__name: "Active"
          bgp_routing_instances:
          - "!create_or_update:autonomous_system__asn": 64500
            "!ref": "device2-instance"

        bgp_peerings:
        - "!bgp_peering":
              endpoint_a:
                  "!create_or_update:routing_instance__device__name": "device1"
                  "!create_or_update:source_ip":
                      "!get:interface__device__name": "device1"
                      "!get:interface__name": "Ethernet1/1"
              endpoint_z:
                  "!create_or_update:routing_instance__device__name": "device2"
                  "!create_or_update:source_ip":
                      "!get:interface__device__name": "device2"
                      "!get:interface__name": "Ethernet1/1"
          status__name: "Active"
        """
        from nautobot_bgp_models.models import Peering  # pylint: disable=import-outside-toplevel

        design = yaml.safe_load(design_template)
        object_creator = Builder(extensions=[BGPPeeringExtension])
        object_creator.implement_design(design, commit=True)
        device1 = Device.objects.get(name="device1")
        device2 = Device.objects.get(name="device2")

        endpoint1 = device1.bgp_routing_instances.first().endpoints.first()
        endpoint2 = device2.bgp_routing_instances.first().endpoints.first()
        self.assertEqual(endpoint1.peering, endpoint2.peering)
        peering_pk = endpoint1.peering.pk
        self.assertEqual(1, Peering.objects.all().count())
        self.assertEqual(endpoint2.peer, endpoint1)
        self.assertEqual(endpoint1.peer, endpoint2)

        # confirm idempotence
        object_creator.implement_design(design, commit=True)
        self.assertEqual(1, Peering.objects.all().count())
        self.assertEqual(peering_pk, Peering.objects.first().pk)
        self.assertEqual(endpoint2.peer, endpoint1)
        self.assertEqual(endpoint1.peer, endpoint2)
