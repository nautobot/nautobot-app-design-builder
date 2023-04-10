"""Unit tests related to template extensions."""
from django.test import TestCase
from django.db.models import Q

from nautobot.tenancy.models import Tenant
from nautobot.ipam.models import Prefix, Role
from nautobot.extras.models import Status
import yaml

from design_builder.design import Builder
from design_builder.ext import NextPrefixExtension


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
        self.server_role = Role.objects.create(name="servers")
        self.video_role = Role.objects.create(name="video")
        self.prefixes = []
        self.prefixes.append(create_prefix("10.0.0.0/8", tenant=self.tenant))
        self.prefixes.append(create_prefix("10.0.0.0/23", tenant=self.tenant, role=self.server_role))
        self.prefixes.append(create_prefix("10.0.2.0/23", tenant=self.tenant, role=self.video_role))

    def test_next_prefix_lookup(self):
        ext = NextPrefixExtension(None)
        want = "10.0.4.0/24"
        got = ext._get_next([self.prefixes[0]], "24")  # pylint:disable=protected-access
        self.assertEqual(want, got)

    def test_next_prefix_lookup_from_full_prefix(self):
        for prefix in ["10.0.0.0/24", "10.0.1.0/24"]:
            create_prefix(prefix)

        prefixes = Prefix.objects.filter(
            Q(network="10.0.0.0", prefix_length=23) | Q(network="10.0.2.0", prefix_length=23)
        )

        ext = NextPrefixExtension(None)
        want = "10.0.2.0/24"
        got = ext._get_next(prefixes, "24")  # pylint:disable=protected-access
        self.assertEqual(want, got)

    def test_creation(self):
        design_template = """
        prefixes:
            - "!next_prefix":
                prefix: "10.0.0.0/23,10.0.2.0/23"
                length: 24
              status__name: "Active"
            - "!next_prefix":
                prefix: "10.0.0.0/23,10.0.2.0/23"
                length: 24
              status__name: "Active"
            - "!next_prefix":
                prefix: "10.0.0.0/23,10.0.2.0/23"
                length: 24
              status__name: "Active"
            - "!next_prefix":
                prefix: "10.0.0.0/23,10.0.2.0/23"
                length: 24
              status__name: "Active"
        """
        design = yaml.safe_load(design_template)
        object_creator = Builder()
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
        object_creator = Builder()
        object_creator.implement_design(design, commit=True)
        self.assertTrue(Prefix.objects.filter(prefix="10.0.2.0/24").exists())
