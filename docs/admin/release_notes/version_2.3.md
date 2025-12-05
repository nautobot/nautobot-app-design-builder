# v2.3 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Changed minimum Nautobot version to 2.4.20.
- Dropped support for Python versions 3.8 and 3.9.

<!-- towncrier release notes start -->
## [v2.3.0 (2025-12-05)](https://github.com/nautobot/nautobot-app-design-builder/releases/tag/v2.3.0)

### Added

- [#219](https://github.com/nautobot/nautobot-app-design-builder/issues/219) - Added a public testing framework by updating and moving DesignTestCase, BuilderChecks.
- [#219](https://github.com/nautobot/nautobot-app-design-builder/issues/219) - Added to public testing framework by creating a small convenience method VerifyDesignTestCase.

### Fixed

- [#204](https://github.com/nautobot/nautobot-app-design-builder/issues/204) - Fixed a problem when creating rack reservations.
- [#253](https://github.com/nautobot/nautobot-app-design-builder/issues/253) - Fixed multiple search and filtering bugs.

### Documentation

- [#219](https://github.com/nautobot/nautobot-app-design-builder/issues/219) - Documented a public testing and checks framework.

### Housekeeping

- [#228](https://github.com/nautobot/nautobot-app-design-builder/issues/228) - Added Virtualization examples in tests.
- [#244](https://github.com/nautobot/nautobot-app-design-builder/issues/244) - Implemented Component UI for detail views.
- [#566](https://github.com/nautobot/nautobot-app-design-builder/issues/566) - Pinned Django debug toolbar to <6.0.0.
- Rebaked from the cookie `nautobot-app-v2.4.2`.
- Rebaked from the cookie `nautobot-app-v2.5.0`.
- Rebaked from the cookie `nautobot-app-v2.5.1`.
- Rebaked from the cookie `nautobot-app-v2.6.0`.
- Rebaked from the cookie `nautobot-app-v2.7.0`.
- Rebaked from the cookie `nautobot-app-v2.7.1`.
- Rebaked from the cookie `nautobot-app-v2.7.2`.
