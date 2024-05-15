"""Choices used within Design Builder."""

from nautobot.utilities.choices import ChoiceSet


class DeploymentStatusChoices(ChoiceSet):
    """Status choices for Designs Instances."""

    ACTIVE = "Active"
    DISABLED = "Disabled"
    DECOMMISSIONED = "Decommissioned"

    CHOICES = (
        (ACTIVE, ACTIVE),
        (DISABLED, DISABLED),
        (DECOMMISSIONED, DECOMMISSIONED),
    )

class DesignModeChoices(ChoiceSet):
    """Status choices for Designs Instances."""

    CLASSIC = "classic"
    DEPLOYMENT = "deployment"

    CHOICES = (
        (CLASSIC, "Classic Behavior"),
        (DEPLOYMENT, "Design Deployment"),
    )
