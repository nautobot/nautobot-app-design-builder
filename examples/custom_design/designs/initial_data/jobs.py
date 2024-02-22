"""Initial data required for core sites."""

from nautobot_design_builder.design_job import DesignJob
from nautobot.extras.jobs import IntegerVar, StringVar

from .context import InitialDesignContext


class InitialDesign(DesignJob):
    """Initialize the database with default values needed by the core site designs."""

    routers_per_site = IntegerVar(min_value=1, max_value=6)
    custom_description = StringVar()

    class Meta:
        """Metadata needed to implement the backbone site design."""

        name = "Initial Data"
        commit_default = False
        design_file = "designs/0001_design.yaml.j2"
        context_class = InitialDesignContext
