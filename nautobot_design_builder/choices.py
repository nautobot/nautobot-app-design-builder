"""Choices used within Design Builder."""

from nautobot.utilities.choices import ChoiceSet


class DesignInstanceStatusChoices(ChoiceSet):
    """Status choices for Designs Instances."""

    ACTIVE = "Active"
    DISABLED = "Disabled"
    DECOMMISSIONED = "Decommissioned"

    CHOICES = (
        (ACTIVE, ACTIVE),
        (DISABLED, DISABLED),
        (DECOMMISSIONED, DECOMMISSIONED),
    )
