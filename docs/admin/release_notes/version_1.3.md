# v1.3.0 Release Notes

## Release Overview

The 1.3 release of Design Builder introduces a new functionality that complements the traditional deployment mode. The designs, if defined for, can now be deployed with life cycle capacity, so after being created, they can be updated with new input data (indefinitely) and decommissioned (i.e., reverting the data to the original state). This new approach requires of new models to track all the information in the database.

Also, as a complement, the design deployments run with the new mode can (optionally) prevent direct modification of the objects or attributes under control of a design. This means that is an object was created by a device, only the design decommissioning can remove it.

## [v1.3.0] - 2024-06

### Added

- Add a new mode that tracks the design deployment providing capacity to updates and decommission (life cycle management)

- Provide data protection (optional) for data that has been created or modified by a design deployment.
