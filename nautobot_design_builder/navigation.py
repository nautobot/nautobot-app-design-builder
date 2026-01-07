"""Navigation."""

from nautobot.apps.ui import (
    NavigationIconChoices,
    NavigationWeightChoices,
    NavMenuGroup,
    NavMenuItem,
    NavMenuTab,
)

menu_items = (
    NavMenuTab(
        name="Designs",
        weight=NavigationWeightChoices.DESIGN,
        icon=NavigationIconChoices.DESIGN,
        groups=(
            NavMenuGroup(
                name="Design Builder",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_design_builder:design_list",
                        name="Designs",
                        weight=100,
                        permissions=["nautobot_design_builder.view_design"],
                        buttons=(),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_design_builder:deployment_list",
                        name="Design Deployments",
                        weight=200,
                        permissions=["nautobot_design_builder.view_deployment"],
                        buttons=(),
                    ),
                ),
            ),
        ),
    ),
)
