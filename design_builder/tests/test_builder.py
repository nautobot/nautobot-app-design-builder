"""Test object creator methods."""
from unittest.mock import Mock, patch
import yaml
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from nautobot.dcim.models import Device, DeviceType, Interface, Manufacturer, Region, Site
from nautobot.extras.choices import RelationshipTypeChoices
from nautobot.extras.models import (
    ConfigContext,
    Relationship,
    RelationshipAssociation,
    Tag,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
)
from nautobot.ipam.models import VLAN, IPAddress, Prefix

from design_builder.design import Builder

INPUT_CREATE_OBJECTS = """
manufacturers:
  - name: "manufacturer1"
  - name: "manufacturer2"

device_types:
  - manufacturer__name: "manufacturer1"
    model: "model name"
    u_height: 1
"""

INPUT_UPDATE_OBJECT = """
device_types:
  - "!update:model": "model name"
    manufacturer__name: "manufacturer2"
"""

INPUT_UPDATE_OBJECT_1 = """
manufacturers:
  - name: "manufacturer1"

device_types:
  - manufacturer__name: "manufacturer1"
    model: "model name"
    u_height: 1
    "!ref": "device"

  - "!update:id": "!ref:device.id"
    model: "new model name"
"""

INPUT_CREATE_NESTED_OBJECTS = """
manufacturers:
  - name: "manufacturer1"

device_types:
  - manufacturer__name: "manufacturer1"
    model: "model name"
    u_height: 1

device_roles:
  - name: "device role"

sites:
  - name: "site_1"
    status__name: "Active"

devices:
  - name: "device_1"
    site__name: "site_1"
    status__name: "Active"
    device_type__model: "model name"
    device_role__name: "device role"
    interfaces:
      - name: "Ethernet1/1"
        type: "virtual"
        status__name: "Active"
        description: "description for Ethernet1/1"
"""

INPUT_UPDATE_NESTED_OBJECTS = """
devices:
  - "!update:name": "device_1"
    interfaces:
      - "!update:name": "Ethernet1/1"
        description: "new description for Ethernet1/1"
"""

INPUT_MANY_TO_MANY_OBJECTS = """
regions:
  - name: "Region 1"
    "!ref": "region_1"

config_contexts:
  - name: "My Context"
    data:
      foo: 123
    regions:
      - "!ref:region_1"
      - name: "My cool new region"
"""

INPUT_ONE_TO_ONE_OBJECTS = """
manufacturers:
  - name: "manufacturer1"

device_types:
  - manufacturer__name: "manufacturer1"
    model: "chassis"
    u_height: 1
    subdevice_role: "parent"

  - manufacturer__name: "manufacturer1"
    model: "card"
    u_height: 0
    subdevice_role: "child"

device_roles:
  - name: "device role"

sites:
  - name: "site_1"
    status__name: "Active"

devices:
  - name: "device_1"
    site__name: "site_1"
    status__name: "Active"
    device_type__model: "chassis"
    device_role__name: "device role"
    devicebays:
      - name: "Bay 1"
        installed_device:
          name: "device_2"
          site__name: "site_1"
          status__name: "Active"
          device_type__model: "card"
          device_role__name: "device role"
"""

INPUT_PREFIXES = """
sites:
  - name: "site_1"
    status__name: "Active"

prefixes:
  - site__name: "site_1"
    status__name: Active
    prefix: "192.168.0.0/24"
  - "!create_or_update:site__name": "site_1"
    "!create_or_update:prefix": "192.168.56.0/24"
    status__name: "Active"
"""

INPUT_INTERFACE_ADDRESSES = """
manufacturers:
  - name: "manufacturer1"

device_types:
  - manufacturer__name: "manufacturer1"
    model: "model name"
    u_height: 1

device_roles:
  - name: "device role"

sites:
  - name: "site_1"
    status__name: "Active"

devices:
  - name: "device_1"
    site__name: "site_1"
    status__name: "Active"
    device_type__model: "model name"
    device_role__name: "device role"
    interfaces:
      - name: "Ethernet1/1"
        type: "virtual"
        status__name: "Active"
        description: "description for Ethernet1/1"
        ip_addresses:
          - address: 192.168.56.1/24
            status__name: "Active"
  """

INPUT_CREATE_TAGS = """
tags:
  - name: Test Tag
    slug: test_tag
    description: Some Description
"""

INPUT_ASSIGN_TAGS = """
tags:
  - name: Test Tag
    "!ref": test_tag
    slug: test_tag
    description: Some Description

sites:
  - name: "site_1"
    status__name: "Active"
    tags:
      - "!ref:test_tag"
"""

INPUT_ASSIGN_TAGS_1 = """
tags:
  - name: "Test Tag"
    slug: "test_tag"
    description: "Some Description"

sites:
  - name: "site_1"
    status__name: "Active"
    tags:
      - { "!get:name": "Test Tag" }
"""

INPUT_CREATE_MLAG = """
manufacturers:
  - name: "manufacturer1"

device_types:
  - manufacturer__name: "manufacturer1"
    model: "model name"
    u_height: 1

device_roles:
  - name: "device role"

sites:
  - name: "site_1"
    status__name: "Active"

devices:
  - name: "device_1"
    site__name: "site_1"
    status__name: "Active"
    device_type__model: "model name"
    device_role__name: "device role"
    interfaces:
      - name: "Ethernet1/1"
        type: "1000base-t"
        status__name: "Active"
        "!ref": "ethernet11"
      - name: "Ethernet2/1"
        type: "1000base-t"
        status__name: "Active"
        "!ref": "ethernet21"
      - name: "Ethernet3/1"
        type: "1000base-t"
        status__name: "Active"
        "!ref": "ethernet31"
      - name: "Ethernet4/1"
        type: "1000base-t"
        status__name: "Active"
        "!ref": "ethernet41"
      - name: "Port-Channel1"
        type: lag
        status__name: "Active"
        member_interfaces:
          - "!ref:ethernet11"
          - "!ref:ethernet21"
          - "!ref:ethernet31"
          - "!ref:ethernet41"
"""

INPUT_CUSTOM_RELATION = """
vlans:
  - "!create_or_update:vid": 42
    name: "The Answer"
    status__name: "Active"

devices:
  - "!create_or_update:name": "device_1"
    "device-to-vlans":
      - "!get:vid": 42
      - vid: "43"
        name: "Better Answer"
        status__name: "Active"
"""

INPUT_REF_FOR_CREATE_OR_UPDATE = """
# Secrets & Secrets Groups
secrets:
- "!create_or_update:name": "Device username"
  "description": "Username for network devices"
  "provider": "environment-variable"
  "parameters": {"variable": "NAUTOBOT_NAPALM_USERNAME"}
  "!ref": "device_username"
- "!create_or_update:name": "Device password"
  "description": "Password for network devices"
  "provider": "environment-variable"
  "parameters": {"variable": "NAUTOBOT_NAPALM_PASSWORD"}
  "!ref": "device_password"

secrets_groups:
- "!create_or_update:name": "Device credentials"
  "!ref": "device_credentials"

secrets_group_associations:
- "!create_or_update:group": "!ref:device_credentials"
  "!create_or_update:secret": "!ref:device_username"
  "access_type": "Generic"
  "secret_type": "username"
- "!create_or_update:group": "!ref:device_credentials"
  "!create_or_update:secret": "!ref:device_password"
  "access_type": "Generic"
  "secret_type": "password"
"""

INPUT_REF_FOR_CREATE_OR_UPDATE1 = """
secrets_groups:
- "!create_or_update:name": "Device credentials"
  secrets:
    - access_type: "Generic"
      secret_type: "username"
      secret:
        "name": "Device username"
        "description": "Username for network devices"
        "provider": "environment-variable"
        "parameters": {"variable": "NAUTOBOT_NAPALM_USERNAME"}
    - access_type: "Generic"
      secret_type: "password"
      secret:
        "name": "Device password"
        "description": "Password for network devices"
        "provider": "environment-variable"
        "parameters": {"variable": "NAUTOBOT_NAPALM_PASSWORD"}
"""


class TestProvisioner(TestCase):
    builder = None

    def implement_design(self, design_input, commit=True):
        """Convenience function for implementing a design."""
        self.builder = Builder()
        self.builder.implement_design(design=yaml.safe_load(design_input), commit=commit)

    def test_create(self):
        self.implement_design(INPUT_CREATE_OBJECTS)

        for want in ["manufacturer1", "manufacturer2"]:
            got = Manufacturer.objects.get(name=want).name
            self.assertEqual(want, got)

        got = DeviceType.objects.first().manufacturer
        want = Manufacturer.objects.get(name="manufacturer1")
        self.assertEqual(want, got)

    def test_update(self):
        self.implement_design(INPUT_CREATE_OBJECTS)
        self.implement_design(INPUT_UPDATE_OBJECT)
        got = DeviceType.objects.first().manufacturer
        want = Manufacturer.objects.get(name="manufacturer2")
        self.assertEqual(want, got)

    def test_update_with_ref(self):
        self.implement_design(INPUT_UPDATE_OBJECT_1)
        want = "new model name"
        got = DeviceType.objects.first().model
        self.assertEqual(want, got)

    def test_nested_create(self):
        self.implement_design(INPUT_CREATE_NESTED_OBJECTS)

        site = Site.objects.get(name="site_1")
        device = Device.objects.get(name="device_1")
        self.assertEqual(site, device.site)

        interface = Interface.objects.get(name="Ethernet1/1")
        self.assertEqual(list(device.interfaces.all()), [interface])

    def test_nested_update(self):
        self.implement_design(INPUT_CREATE_NESTED_OBJECTS)
        interface = Interface.objects.get(name="Ethernet1/1")
        self.assertEqual("description for Ethernet1/1", interface.description)

        self.implement_design(INPUT_UPDATE_NESTED_OBJECTS)

        interface.refresh_from_db()
        self.assertEqual("new description for Ethernet1/1", interface.description)

    def test_many_to_many(self):
        self.implement_design(INPUT_MANY_TO_MANY_OBJECTS)
        region = Region.objects.first()
        context = ConfigContext.objects.first()

        self.assertIn(region, context.regions.all())
        try:
            Region.objects.get(name="My cool new region")
        except ObjectDoesNotExist:
            self.fail("Failed to find newly created region")

    def test_one_to_one(self):
        self.implement_design(INPUT_ONE_TO_ONE_OBJECTS)
        device = Device.objects.all()[0]
        want = Device.objects.all()[1]
        self.assertEqual(1, len(device.devicebays.all()))

        got = device.devicebays.first().installed_device
        self.assertEqual(want, got)

    def test_prefixes(self):
        self.implement_design(INPUT_PREFIXES)
        want = "192.168.0.0/24"
        got = str(Prefix.objects.all()[0])
        self.assertEqual(want, got)

        want = "192.168.56.0/24"
        got = str(Prefix.objects.all()[1])
        self.assertEqual(want, got)

    def test_interface_addresses(self):
        self.implement_design(INPUT_INTERFACE_ADDRESSES)
        want = "192.168.56.1/24"
        address = IPAddress.objects.get(address="192.168.56.1/24")
        got = str(address)
        self.assertEqual(want, got)

        want = [address]
        got = list(Interface.objects.first().ip_addresses.all())
        self.assertEqual(want, got)

    def test_create_tags(self):
        self.implement_design(INPUT_CREATE_TAGS)
        want = "Some Description"
        tag = Tag.objects.get(name="Test Tag")
        got = tag.description
        self.assertEqual(want, got)

    def test_assign_tags(self):
        self.implement_design(INPUT_ASSIGN_TAGS)
        tag = Tag.objects.get(name="Test Tag")
        site = Site.objects.first()
        self.assertIn(tag, list(site.tags.all()))

    def test_assign_tags_by_name(self):
        self.implement_design(INPUT_ASSIGN_TAGS_1)
        tag = Tag.objects.get(name="Test Tag")
        site = Site.objects.first()
        self.assertIn(tag, list(site.tags.all()))

    def test_create_mlag(self):
        self.implement_design(INPUT_CREATE_MLAG)
        device = Device.objects.get(name="device_1")
        lag = device.interfaces.get(name="Port-Channel1")
        self.assertEqual(4, lag.member_interfaces.count())
        interfaces = [i.name for i in lag.member_interfaces.all()]
        for i in range(1, 5):
            self.assertIn(f"Ethernet{i}/1", interfaces)

    def test_custom_relation(self):
        device_type = ContentType.objects.get_for_model(Device)
        relationship, _ = Relationship.objects.get_or_create(
            name="Device to VLANS",
            defaults={
                "slug": "device-to-vlans",
                "type": RelationshipTypeChoices.TYPE_MANY_TO_MANY,
                "source_type": device_type,
                "destination_type": ContentType.objects.get_for_model(VLAN),
            },
        )
        self.implement_design(INPUT_CREATE_NESTED_OBJECTS)
        self.implement_design(INPUT_CUSTOM_RELATION)
        vlan42 = VLAN.objects.get(vid=42)
        vlan43 = VLAN.objects.get(vid=43)

        device = Device.objects.get(name="device_1")
        query_params = {"relationship": relationship, "source_id": device.pk, "source_type": device_type}
        vlans = [obj.destination for obj in RelationshipAssociation.objects.filter(**query_params)]
        self.assertIn(vlan42, vlans)
        self.assertIn(vlan43, vlans)

    @patch("design_builder.design.Builder.roll_back")
    def test_simple_design_roll_back(self, roll_back: Mock):
        self.implement_design(INPUT_CREATE_OBJECTS, False)
        roll_back.assert_called()

    def test_create_or_update_with_ref(self):
        # run it twice to make sure it is idempotent
        for _ in range(2):
            self.implement_design(INPUT_REF_FOR_CREATE_OR_UPDATE)
            self.assertEqual(2, len(Secret.objects.all()))
            self.assertEqual(1, len(SecretsGroup.objects.all()))
            self.assertEqual(2, len(SecretsGroupAssociation.objects.all()))
