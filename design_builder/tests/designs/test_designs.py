from design_builder.base import DesignJob
from design_builder.ext import Extension


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


class CustomExtension(Extension):
    attribute_tag = "custom_extension"


class DesignJobWithExtensions(DesignJob):
    class Meta:
        name = "Design with Custom Extensions"
        design_file = "templates/simple_design.yaml.j2"
        extensions = [CustomExtension]
