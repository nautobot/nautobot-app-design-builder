"""Test Design Filter."""

from nautobot.apps.testing import FilterTestCases

from nautobot_design_builder import filters, models
from nautobot_design_builder.tests import fixtures


class DesignFilterTestCase(FilterTestCases.FilterTestCase):  # pylint: disable=too-many-ancestors
    """Design Filter Test Case."""

    queryset = models.Design.objects.all()
    filterset = filters.DesignFilterSet
    generic_filter_tests = (
        ("id",),
        ("created",),
        ("last_updated",),
        ("name",),
    )

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
