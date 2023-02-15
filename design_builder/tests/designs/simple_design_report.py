from design_builder.base import DesignJob


class SimpleDesignReport(DesignJob):
    class Meta:
        name = "Simple Design"
        design_file = "templates/simple_design.yaml.j2"
        report = "templates/simple_report.md.j2"
