"""Choices used within Design Builder."""

from nautobot.apps.choices import ChoiceSet


class DeploymentStatusChoices(ChoiceSet):
    """Status choices for Designs Instances."""

    ACTIVE = "Active"
    DISABLED = "Disabled"
    DECOMMISSIONED = "Decommissioned"

    CHOICES = (
        (None, "Unknown"),
        (ACTIVE, ACTIVE),
        (DISABLED, DISABLED),
        (DECOMMISSIONED, DECOMMISSIONED),
    )


class DesignModeChoices(ChoiceSet):
    """Status choices for Designs Instances."""

    CLASSIC = "classic"
    DEPLOYMENT = "deployment"

    CHOICES = (
        (CLASSIC, "Ad-Hoc"),
        (DEPLOYMENT, "Design Deployment"),
    )
