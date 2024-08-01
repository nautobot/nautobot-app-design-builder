# v1.4.0 Release Notes

## Release Overview

The 1.4 release of Design Builder introduces new functionality that expands on the deployment mode introduced in 1.3. Pre-existing data (i.e. data not created by a design, or created by one not in deployment mode) can now be imported into a design deployment. This design deployment then owns the lifecycle of that data just like if it had been created by it.

As a compliment on the other end of the lifecycle, the design decommissioning now has a checkbox for `delete` functionality. By default this is checked, which causes the decommissioning job to function as it did prior to the introduction of this feature. If you uncheck it, the data is unlinked from the design deployment, but _not_ deleted, somewhat like a reverse import.


## [v1.4.0] - 2024-07

### Added

- Adds import functionality to deployment mode designs
- Adds the possibility to merely unlink and not delete objects associated with a design deployment during decommissioning 
