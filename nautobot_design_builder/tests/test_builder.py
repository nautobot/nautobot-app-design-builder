"""Test object creator methods."""

import os

from nautobot_design_builder.testing import BuilderTestCase


class TestGeneralDesigns(BuilderTestCase):
    """Designs that should work with all versions of Nautobot."""

    data_dir = os.path.join(os.path.dirname(__file__), "testdata")
