# v1.1.0 Release Notes

## Release Overview

The 1.1 release of Design Builder mostly includes performance improvements in the implementation system. There is a breaking change related to one-to-one relationships. Prior to the 1.1 release, one-to-one relationships were not saved until after the parent object was saved. The performance optimization work revealed this as a performance issue and now one-to-one relationships are treated as simple foreign keys. Since foreign key saves are not deferred by default, it may now be necessary to explicitly specify deferring the save operation. A new `deferred` attribute has been introduced that causes design builder to defer saving the foreign-key relationship until after the parent object has been saved. The one known case that is affected by this change is when setting a device primary IP when the IP itself is created as a member of an interface in the same device block. See unit tests and design examples for further explanation.

Additionally, the `design.Builder` class has been renamed to `design.Environment` to better reflect what that class does. A `Builder` alias has been added to `Environment` for backwards compatibility with a deprecation warning.

## [v1.1.0] - 2024-04

### Added

- Added `deferred` attribute to allow deferral of field assignment. See notes in the Changed section.

- Added `model_metadata` attribute to models. At the moment, this provides the ability to specify additional arguments passed to the `save` method of models being updated. The known use case for this is in creating Git repositories in Nautobot 1.x where `trigger_resync` must be `False`. In the future, additional fields will be added to `model_metadata` to provide new functionality.

### Changed

- Renamed `nautobot_design_builder.design.Builder` to `nautobot_design_builder.Environment` - aliased original name with deprecation warning.

- Any designs that set `OneToOne` relationships (such as device `primary_ip4`) may now need a `deferred: true` statement in their design for those fields. Previously, `OneToOne` relationships were always deferred and this is usually unnecessary. Any deferrals must now be explicit.

- Design reports are now saved to the file `report.md` for Nautobot 2.x installations.
