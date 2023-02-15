from design_builder.base import DesignJob


class SimpleDesign(DesignJob):
    class Meta:
        name = "Simple Design"
        design_file = "templates/simple_design.yaml.j2"
