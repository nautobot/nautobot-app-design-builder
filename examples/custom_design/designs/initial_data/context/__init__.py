from nautobot_design_builder.context import Context


class InitialDesignContext(Context):
    """Render context for basic design"""

    routers_per_site: int
    custom_description = str
