# v1.1.0 Release Notes

## Release Overview

- 

## [v1.6.0] - 2023-09

### Added

- Added `deferred` attribute to allow deferral of field assignment. See notes in the Changed section.

- Added `model_metadata` attribute to models. At the moment, this provides the ability to specify additional arguments passed to the `save` method of models being updated. The known use case for this is in creating Git repositories in Nautobot 1.x where `trigger_resync` must be `False`. In the future, additional fields will be added to `model_metadata` to provide new functionality.

### Changed

- Renamed `nautobot_design_builder.design.Builder` to `nautobot_design_builder.Environment` - aliased original name with deprecation warning.

- Any designs that set `OneToOne` relationships (such as device `primary_ip4`) may now need a `deferred: true` statement in their design for those fields. Previously, `OneToOne` relationships were always deferred and this is usually unnecessary. Any deferrals must now be explicit.

- Design reports are now saved to the file `report.md` for Nautobot 2.x installations.
