from design_builder.base import DesignJob


class SimpleDesign(DesignJob):
    class Meta:
        name = "Simple Design"
        design_file = "templates/simple_design.yaml.j2"


class SimpleDesignReport(DesignJob):
    class Meta:
        name = "Simple Design"
        design_file = "templates/simple_design.yaml.j2"
        report = "templates/simple_report.md.j2"


class MultiDesignJob(DesignJob):
    class Meta:
        name = "Simple Design"
        design_files = [
            "templates/simple_design.yaml.j2",
            "templates/simple_design_2.yaml.j2",
        ]


class MultiDesignJobWithError(DesignJob):
    class Meta:
        name = "Simple Design"
        design_files = [
            "templates/simple_design.yaml.j2",
            "templates/simple_design.yaml.j2",
        ]
