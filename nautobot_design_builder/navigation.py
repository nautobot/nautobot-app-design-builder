"""Navigation."""

from nautobot.apps.ui import (
    NavMenuGroup,
    NavMenuItem,
    NavMenuTab,
)


menu_items = (
    NavMenuTab(
        name="Designs",
        weight=1000,
        groups=(
            NavMenuGroup(
                name="Design Builder",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_design_builder:design_list",
                        name="Designs",
                        permissions=["nautobot_design_builder.view_design"],
                        buttons=(),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_design_builder:deployment_list",
                        name="Design Deployments",
                        permissions=["nautobot_design_builder.view_deployment"],
                        buttons=(),
                    ),
                ),
            ),
        ),
    ),
)
