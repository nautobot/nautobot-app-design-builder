"""Basic design demonstrates the capabilities of the Design Builder."""

from nautobot_design_builder.design_job import DesignJob

from .context import DesignContext


class BasicDesign(DesignJob):
    """A basic design for design builder."""

    class Meta:
        """Metadata describing this design job."""

        name = "{{ design_name }} Design"
        commit_default = False
        design_file = "designs/0001_design.yaml.j2"
        context_class = DesignContext
        report = "report.md.j2"
