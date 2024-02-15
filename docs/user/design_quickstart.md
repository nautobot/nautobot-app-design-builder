# Design Quick Start

## Overview

The [Demo Designs](https://github.com/nautobot/demo-designs) repository includes designs that can be used as a starting point for new design repositories. Simply fork the repository and add to or change the existing demo designs. The demo designs includes a full application stack that can be started with `invoke start` similar to Nautobot plugin or core development.

## Adding Designs

To add a new design you will need (at a minimum) a class extending `nautobot_design_builder.base.DesignJob`, a class extending `nautobot_design_builder.context.Context` and a design template. The design job must be imported in the `jobs/__init__.py` and it must also be either in a module in the `jobs` directory or it must be loaded in the `__init__.py` file in a package within the `jobs` directory. This follows the [standard convention](https://docs.nautobot.com/projects/core/en/stable/development/jobs/#writing-jobs) for Nautobot jobs.

For more information on creating designs see [Getting Started with Designs](design_development.md).

## Sample Data

Much of the time, designs will need some data to exist in Nautobot before they can be built. In a development and testing environment it is necessary to generate this data for testing purposes. The Design Builder application comes with a `load_design` management command that will read a design YAML file (not a template) and will build the design in Nautobot. This can be used to produce sample data for a development environment. Simply create a YAML file that includes all of the object definitions needed for testing and load the file with `invoke build-design <filename>`. This should read the file and build all of the objects within Nautobot.
