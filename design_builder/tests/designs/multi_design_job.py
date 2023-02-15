from design_builder.base import DesignJob


class MultiDesignJob(DesignJob):
    class Meta:
        name = "Simple Design"
        design_files = [
            "templates/simple_design.yaml.j2",
            "templates/simple_design_2.yaml.j2",
        ]
