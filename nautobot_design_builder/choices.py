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


class DesignInstanceLiveStateChoices(ChoiceSet):
    """Status choices for Live State Designs Instance."""

    DEPLOYED = "Deployed"
    PENDING = "Pending"
    ROLLBACKED = "Rolled back"

    CHOICES = (
        (DEPLOYED, DEPLOYED),
        (PENDING, PENDING),
        (ROLLBACKED, ROLLBACKED),
    )
