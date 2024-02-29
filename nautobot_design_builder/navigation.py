"""Navigation."""

from nautobot.apps.ui import (
    NavMenuGroup,
    NavMenuItem,
    NavMenuTab,
)


menu_items = (
    NavMenuTab(
        name="Jobs",
        weight=150,
        groups=(
            NavMenuGroup(
                name="Designs",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_design_builder:design_list",
                        name="Designs",
                        permissions=["nautobot_design_builder.view_design"],
                        buttons=(),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_design_builder:designinstance_list",
                        name="Design Instances",
                        permissions=["nautobot_design_builder.view_designinstance"],
                        buttons=(),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_design_builder:journal_list",
                        name="Journals",
                        permissions=["nautobot_design_builder.view_journal"],
                        buttons=(),
                    ),
                ),
            ),
        ),
    ),
)
