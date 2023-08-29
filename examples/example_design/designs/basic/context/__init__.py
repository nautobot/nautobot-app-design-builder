"""This module contains the render context for the basic design."""
from nautobot_design_builder.context import Context, context_file


@context_file("context.yaml")
class DesignContext(Context):
    """Render context for basic design."""
