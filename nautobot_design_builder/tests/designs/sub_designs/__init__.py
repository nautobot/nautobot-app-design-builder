"""Derived context used for unit testing."""
from nautobot_design_builder.context import context_file
from nautobot_design_builder.tests.designs.context import BaseContext


@context_file("sub_design_context_file")
class SubDesignContext(BaseContext):
    "Context that inherits from a base, for unit testing."
