from design_builder.base import DesignJob


class MultiDesignJobWithError(DesignJob):
    class Meta:
        name = "Simple Design"
        design_files = [
            "templates/simple_design.yaml.j2",
            "templates/simple_design.yaml.j2",
        ]
