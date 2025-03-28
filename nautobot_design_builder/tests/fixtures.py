"""Create fixtures for tests."""

from nautobot_design_builder.models import Design


def create_design():
    """Fixture to create necessary number of Design for tests."""
    Design.objects.create(name="Test One")
    Design.objects.create(name="Test Two")
    Design.objects.create(name="Test Three")
