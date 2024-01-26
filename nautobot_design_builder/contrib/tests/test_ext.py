"""Unit tests related to template extensions."""
import os

from django.test import TestCase

from nautobot_design_builder.tests.test_builder import builder_test_case
from nautobot_design_builder.util import nautobot_version


@builder_test_case(os.path.join(os.path.dirname(__file__), "testdata"))
class TestAgnosticExtensions(TestCase):
    """Test contrib extensions against any version of Nautobot."""


@builder_test_case(os.path.join(os.path.dirname(__file__), "testdata", "nautobot_v1"))
class TestV1Extensions(TestCase):
    """Test contrib extensions against Nautobot V1."""

    def setUp(self):
        if nautobot_version >= "2.0.0":
            self.skipTest("These tests are only supported in Nautobot 1.x")
        super().setUp()


@builder_test_case(os.path.join(os.path.dirname(__file__), "testdata", "nautobot_v2"))
class TestV2Extensions(TestCase):
    """Test contrib extensions against Nautobot V2."""

    def setUp(self):
        if nautobot_version < "2.0.0":
            self.skipTest("These tests are only supported in Nautobot 2.x")
        super().setUp()
