

from design_builder.context import context_file
from design_builder.tests.designs.context import BaseContext


@context_file("sub_design_context_file")
class SubDesignContext(BaseContext):
    pass
