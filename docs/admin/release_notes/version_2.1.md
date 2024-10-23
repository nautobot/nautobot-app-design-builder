# v2.1.0 Release Notes

## Release Overview

The 2.1.0 release of Design Builder is the first release in the 2.x series to include the design lifecycle features previously introduced in v1.3.0. This feature provides a means to track objects created or updated by designs in a collection of Nautobot objects known as a deployment. These deployments can be managed by re-running the design with new variables, and they can also be decommissioned. Objects and attributes that are owned by a deployment are protected from outside changes.

## [v2.1.0] - 2024-10

### Added

- Added design deployment mechanism to track objects that are part of a design deployment.

- Added custom validator to protect objects and attributes that are owned, or managed, by a design deployment.

- Added the ability to import existing objects into a design deployment. This is particularly useful when a new design should encapsulate objects from a brownfield deployment.
