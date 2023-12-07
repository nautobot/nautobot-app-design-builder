# Design Quick Start

## Overview

The Design Builder source repository includes an example design that can be used as a starting point for new design repositories. Simply copy the directory `examples/example_design` and commit the code to a new design repository. The example design includes a full application stack that can be started with `invoke start` similar to Nautobot plugin or core development.

## Project Structure

The example design directory structure is as follows:

```plain
├── README.md
├── designs
│   ├── __init__.py
│   ├── basic_design.py
│   ├── context.py
│   ├── context.yaml
│   ├── templates
│   │   ├── basic_design.yaml.j2
│   │   └── basic_design_report.md.j2
│   └── tests
│       └── __init__.py
└── jobs
    ├── __init__.py
    └── designs.py
```

Nothing within the `jobs` directory should ever need to be updated. All design related files live within the `designs` directory. One design and one report are available in this example job with a simple design context.

## Adding Designs

To add a new design you will need (at a minimum) a class extending `nautobot_design_builder.base.DesignJob`, a class extending `nautobot_design_builder.context.Context` and a design template. The organization of these components within Python modules and packages is not relevant, as long as the design job exists in a module somewhere in the main `designs/` directory then it should be automatically discovered by the Design Builder application. For more information on creating designs see [Getting Started with Designs](design_development.md).

## Sample Data

Much of the time, designs will need some data to exist in Nautobot before they can be built. In a development and testing environment it is necessary to generate this data for testing purposes. The Design Builder application comes with a `load_design` management command that will read a design YAML file (not a template) and will build the design in Nautobot. This can be used to produce sample data for a development environment. Simply create a YAML file that includes all of the object definitions needed for testing and load the file with `invoke build-design <filename>`. This should read the file and build all of the objects within Nautobot.

## Testing Designs

Unit tests for designs can be easily developed. The example design includes a single unit test that can be used as a starting point.

```python
--8<-- "examples/example_design/designs/tests/__init__.py"
```

Design unit tests should inherit from `nautobot_design_builder.tests.DesignTestCase` and use the `get_mocked_job(<design class>)` to get a callable for testing. Simply call the returned mock job and supply any necessary inputs for the `data` argument (these inputs should match whatever job vars are defined on the design job). Be careful with the `commit` argument, if you expect objects to be available after the job runs then it must be set to `True`. Each unit test should run a design job and then test for changes to the database using standard Django ORM model queries.

## Config Contexts

Testing designs that include config context generation for a git repository can be done with a local git repository. An invoke task is included with the example design that will create a local repo and make it available in Nautobot. Call `invoke create-local-repo <repo name>` and the task will create the repo, check it out to the `repos/` directory and make it available in Nautobot.
