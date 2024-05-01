"""Unit tests related to template extensions."""

import os

from django.test import TestCase

from nautobot_design_builder.tests.test_builder import builder_test_case


@builder_test_case(os.path.join(os.path.dirname(__file__), "testdata"))
class TestAgnosticExtensions(TestCase):
    """Test contrib extensions."""
