"""Base DesignContext for testing."""
from nautobot_design_builder.context import Context, context_file


@context_file("base_context_file")
class BaseContext(Context):
    """Empty context that loads the base_context_file."""
