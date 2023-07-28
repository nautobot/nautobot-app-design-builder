"""Choices used within Design Builder."""
from nautobot.utilities.choices import ChoiceSet


class DesignStatusChoices(ChoiceSet):
    """Status choices for Designs."""

    PENDING = "Pending"
    ACTIVE = "Active"
    DISABLED = "Disabled"
    DECOMMISSIONED = "Decommissioned"

    CHOICES = (
        (PENDING, PENDING),
        (ACTIVE, ACTIVE),
        (DISABLED, DISABLED),
        (DECOMMISSIONED, DECOMMISSIONED),
    )
