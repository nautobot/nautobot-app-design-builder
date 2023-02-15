"""Basic design demonstrates the capabilities of the Design Builder."""

from design_builder.base import DesignJob

from .context import DesignContext


class BasicDesign(DesignJob):
    """A basic design for design builder."""

    class Meta:
        """Metadata describing this design job."""

        name = "{{ design_name }} Design"
        commit_default = False
        design_file = "templates/basic_design.yaml.j2"
        context_class = DesignContext
        report = "templates/basic_design_report.md.j2"
