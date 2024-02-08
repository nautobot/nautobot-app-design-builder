"""Unit tests for designs"""

from nautobot_design_builder.tests import DesignTestCase

from ..basic.design import BasicDesign


class TestBasicDesign(DesignTestCase):
    def test_design(self):
        job = self.get_mocked_job(BasicDesign)
        job.run({}, True)
        self.assertTrue(True)
