"""Unit tests related to template extensions."""
from django.test import TestCase

from nautobot.ipam.models import Prefix
from nautobot.extras.models import Status
import yaml
from design_builder.design import Builder

from design_builder.ext import NextPrefixExtension

from design_builder.jinja2 import new_template_environment


class TestNextPrefixExtension(TestCase):
    def test_next_prefix_lookup(self):
        Prefix.objects.get_or_create(
            prefix="10.0.0.0/8", 
            defaults={
                "status": Status.objects.get(name="Active")
            }
        )
        ext = NextPrefixExtension(None)
        want = "10.0.0.0/24"
        got = ext.value("10.0.0.0/8", "24")
        self.assertEqual(want, got)

    def test_next_prefix_lookup_from_full_prefix(self):
        for prefix in ["10.0.0.0/23", "10.0.0.0/24", "10.0.1.0/24", "10.0.2.0/23"]:
            Prefix.objects.get_or_create(
                prefix=prefix,
                defaults={
                    "status": Status.objects.get(name="Active")
                }
            )
        
        ext = NextPrefixExtension(None)
        want = "10.0.2.0/24"
        got = ext.value("10.0.0.0/23, 10.0.2.0/23", "24")
        self.assertEqual(want, got)

    def test_creation(self):
        design_template = """
        prefixes:
            - prefix: 10.0.0.0/23
              status__name: "Active"
            - prefix: 10.0.2.0/23
              status__name: "Active"
            - prefix: "!next_prefix:10.0.0.0/23,10.0.2.0/23:24"
              status__name: "Active"
            - prefix: "!next_prefix:10.0.0.0/23,10.0.2.0/23:24"
              status__name: "Active"
            - prefix: "!next_prefix:10.0.0.0/23,10.0.2.0/23:24"
              status__name: "Active"
            - prefix: "!next_prefix:10.0.0.0/23,10.0.2.0/23:24"
              status__name: "Active"
        """
        design = yaml.safe_load(design_template)
        object_creator = Builder()
        object_creator.implement_design(design)
        self.assertTrue(Prefix.objects.filter(prefix="10.0.0.0/24").exists())
        self.assertTrue(Prefix.objects.filter(prefix="10.0.1.0/24").exists())
        self.assertTrue(Prefix.objects.filter(prefix="10.0.2.0/24").exists())
        self.assertTrue(Prefix.objects.filter(prefix="10.0.3.0/24").exists())
    