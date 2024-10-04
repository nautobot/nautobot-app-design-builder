"""Unit tests related to template extensions."""

import os

from nautobot_design_builder.tests.test_builder import BuilderTestCase


class TestContribExtensions(BuilderTestCase):
    """Test contrib extensions against any version of Nautobot."""

    data_dir = os.path.join(os.path.dirname(__file__), "testdata")
