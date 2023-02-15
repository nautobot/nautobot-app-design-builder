from design_builder.base import DesignJob

from .initial_context import InitialDesignContext


class InitialDesign(DesignJob):
    class Meta:
        name = "Initial Data"
        commit_default = False
        design_file = "templates/initial_design.yaml.j2"
        context_class = InitialDesignContext
