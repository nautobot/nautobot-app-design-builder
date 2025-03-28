"""Menu items."""

from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab

items = (
    NavMenuItem(
        link="plugins:nautobot_design_builder:design_list",
        name="Nautobot Design Builder",
        permissions=["nautobot_design_builder.view_design"],
        buttons=(
            NavMenuAddButton(
                link="plugins:nautobot_design_builder:design_add",
                permissions=["nautobot_design_builder.add_design"],
            ),
        ),
    ),
)

menu_items = (
    NavMenuTab(
        name="Apps",
        groups=(NavMenuGroup(name="Nautobot Design Builder", items=tuple(items)),),
    ),
)
