# v2.1.0 Release Notes

## Release Overview

The 2.1.0 release of Design Builder is the first release in the 2.x series to include the design lifecycle features previously introduced in v1.3.0. This feature provides a means to track objects created or updated by designs in a collection of Nautobot objects known as a deployment. These deployments can be managed by re-running the design with new variables, and they can also be decommissioned. Objects and attributes that are owned by a deployment are protected from outside changes.

## [v2.1.1 (2025-03-21)](https://github.com/nautobot/nautobot-app-design-builder/releases/tag/v2.1.1)

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

## [v2.1.0] - 2024-10

### Added

- Added design deployment mechanism to track objects that are part of a design deployment.

- Added custom validator to protect objects and attributes that are owned, or managed, by a design deployment.

- Added the ability to import existing objects into a design deployment. This is particularly useful when a new design should encapsulate objects from a brownfield deployment.
