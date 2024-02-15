"""Test 1."""

from nautobot_design_builder.design_job import DesignJob

from .context import CreateBaselineContext


class CreateBaseline(DesignJob):
    """Class CreateBaseline."""

    class Meta:
        """Meta design."""

        name = "Create Baseline"
        commit_default = False
        design_file = "designs/create_baseline_design.yaml.j2"
        context_class = CreateBaselineContext
