"""Choices used within Design Builder."""
from nautobot.utilities.choices import ChoiceSet


class DesignInstanceStatusChoices(ChoiceSet):
    """Status choices for Designs Instance."""

    ACTIVE = "Active"
    DISABLED = "Disabled"
    DECOMMISSIONED = "Decommissioned"

    CHOICES = (
        (ACTIVE, ACTIVE),
        (DISABLED, DISABLED),
        (DECOMMISSIONED, DECOMMISSIONED),
    )


class DesignInstanceOperStatusChoices(ChoiceSet):
    """Status choices for Operational Designs Instance."""

    DEPLOYED = "Deployed"
    PENDING = "Pending"
    ROLLBACKED = "Rollbacked"

    CHOICES = (
        (DEPLOYED, DEPLOYED),
        (PENDING, PENDING),
        (ROLLBACKED, ROLLBACKED),
    )
