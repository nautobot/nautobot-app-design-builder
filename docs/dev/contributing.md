# Contributing to the App

Contributions are encouraged and we are always delighted in any form of work. We are always looking for feedback both in the development of code as well as documentation, use cases, and examples. To contribute to this project, please use the following guidlines:

## Code Development

The project is packaged with a light [development environment](dev_environment.md) based on `docker-compose` to help with the local development of the project and to run tests.

The project is following Network to Code software development guidelines and is leveraging the following:

- Python linting and formatting: `black`, `pylint`, `bandit`, `flake8`, and `pydocstyle`.
- YAML linting is done with `yamllint`.
- Django unit test to ensure the plugin is working properly.

Documentation is built using [mkdocs](https://www.mkdocs.org/). The [Docker based development environment](dev_environment.md#docker-development-environment) automatically starts a container hosting a live version of the documentation website on [http://localhost:8001](http://localhost:8001) that auto-refreshes when you make any changes to your local files.

## Documentation

Code documentation follows the [Google docstring](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) style. Where possible, include a description, argument documentation and examples.

The user and developer documentation is located in the top level `docs/` directory. The documenation is written in markdown format and is rendered using MkDocs.

Example designs should be placed in the top level `examples/` directory, as appropriate.

## Branching Policy

The branching policy includes the following tenets:

- The `develop` branch is the branch of the next major and minor paired version planned.
- PRs intended to add new features should be sourced from the `develop` branch.
- PRs intended to fix issues in the Nautobot LTM compatible release should be sourced from the latest `ltm-<major.minor>` branch instead of `develop`.

## Release Policy

There is no set release schedule for this App. New releases will be published as appropriate when new features and/or bug fixes are ready.
