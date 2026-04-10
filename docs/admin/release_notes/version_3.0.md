# v3.0 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

This major release marks the compatibility of the Design Builder App with Nautobot 3.0.0. Check out the [full details](https://docs.nautobot.com/projects/core/en/stable/release-notes/version-3.0/) of the changes included in this new major release of Nautobot. Highlights:

- Minimum Nautobot version supported is 3.0.
- Added support for Python 3.13 and removed support for 3.9.
- Updated UI framework to use latest Bootstrap 5.3.

We will continue to support the previous major release for users of Nautobot LTM 2.4 only with critical bug and security fixes as per the [Software Lifecycle Policy](https://networktocode.com/company/legal/software-lifecycle-policy/).

<!-- towncrier release notes start -->

## [v3.0.1 (2026-04-10)](https://github.com/nautobot/nautobot-app-design-builder/releases/tag/v3.0.1)

### Added

- [#234](https://github.com/nautobot/nautobot-app-design-builder/issues/234) - Added `next_ip` action tag
- [#270](https://github.com/nautobot/nautobot-app-design-builder/issues/270) - Added panels to various models to indicate Design Deployment membership.

### Fixed

- [#212](https://github.com/nautobot/nautobot-app-design-builder/issues/212) - Fixed display of design model meta information.
- [#258](https://github.com/nautobot/nautobot-app-design-builder/issues/258) - Fixed code injection vulnerability
- [#268](https://github.com/nautobot/nautobot-app-design-builder/issues/268) - Fixed dropdown menu under "Decommission Design Deployments" job.
- [#273](https://github.com/nautobot/nautobot-app-design-builder/issues/273) - Fixed test using deprecated Django make_random_password function.

### Documentation

- [#229](https://github.com/nautobot/nautobot-app-design-builder/issues/229) - Documented `design_mode` and how to enable deployment mode
- [#264](https://github.com/nautobot/nautobot-app-design-builder/issues/264) - Added a note to only use unique model fields in the update and update_or_create tags.
- [#265](https://github.com/nautobot/nautobot-app-design-builder/issues/265) - Updated Design builder documentation to include 3.0 screenshots.

### Housekeeping

- Rebaked from the cookie `nautobot-app-v3.0.0`.
- Rebaked from the cookie `nautobot-app-v3.1.2`.
- Rebaked from the cookie `nautobot-app-v3.1.3`.

## [v3.0.0 (2025-11-17)](https://github.com/nautobot/nautobot-app-design-builder/releases/tag/v3.0.0)

### Added

- Added support for Nautobot 3.0.
- Added support for Python 3.13.

## [v3.0.0a1 (2025-10-05)](https://github.com/nautobot/nautobot-app-design-builder/releases/tag/v3.0.0a1)
