"""Test Design Filter."""

from django.test import TestCase

from nautobot_design_builder import filters, models
from nautobot_design_builder.tests import fixtures


class DesignFilterTestCase(TestCase):
    """Design Filter Test Case."""

    queryset = models.Design.objects.all()
    filterset = filters.DesignFilterSet

    @classmethod
    def setUpTestData(cls):
        """Setup test data for Design Model."""
        fixtures.create_design()

    def test_q_search_name(self):
        """Test using Q search with name of Design."""
        params = {"q": "Test One"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_q_invalid(self):
        """Test using invalid Q search for Design."""
        params = {"q": "test-five"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 0)
