# v2.2.0 Release Notes

## Release Overview

The 2.2.0 release of Design Builder introduces a change in the Jinja2 filters location according to Nautobot standards.

Before this release, the Jinja2 filters were located in the `nautobot_design_builder.jinja2` module. This release moves the filters to the `nautobot_design_builder.jinja_filters` module.

## [v2.2.0 (2025-03-25)](https://github.com/nautobot/nautobot-app-design-builder/releases/tag/v2.2.0)

### Added

- [#200](https://github.com/nautobot/nautobot-app-design-builder/issues/200) - Error reporting for custom relationships that introduce duplicate fields

### Fixed

- [#203](https://github.com/nautobot/nautobot-app-design-builder/issues/203) - Provided a default value for the `dry_run` keyword argument
- [#214](https://github.com/nautobot/nautobot-app-design-builder/issues/214) - Provided a default value for the `dry_run` keyword argument
- [#217](https://github.com/nautobot/nautobot-app-design-builder/issues/217) - Fix APIView tests overwritting `test_list_objects_depth_0`
- [#218](https://github.com/nautobot/nautobot-app-design-builder/issues/218) - Fix issue with model of with attribute of `filter` overlapping with `ModelMetadata` class.

### Housekeeping

- [#196](https://github.com/nautobot/nautobot-app-design-builder/issues/196) - Updates docs dependencies to cookiecutter versions so the RTD build will pass.
- [#196](https://github.com/nautobot/nautobot-app-design-builder/issues/196) - Fixes #187, removing Nautobot as an extra and setting the upper bound to 3.0.
- [#201](https://github.com/nautobot/nautobot-app-design-builder/issues/201) - Refactored jinja2 filters to Nautobot standard location
- [#202](https://github.com/nautobot/nautobot-app-design-builder/issues/202) - Adds tests for properties in render contexts
- [#221](https://github.com/nautobot/nautobot-app-design-builder/issues/221) - Rebake the testing dependencies from the cookie to get docs working.
