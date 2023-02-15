# Design Builder

<p align="center">
  <img src="/docs/images/icon-design-builder.png" class="logo" height="200px">
  <br>
  <a href="https://github.com/networktocode-llc/nautobot-plugin-design-builder/actions"><img src="https://github.com/networktocode-llc/nautobot-plugin-design-builder/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="https://docs.nautobot.com/projects/design-builder/en/latest"><img src="https://readthedocs.org/projects/nautobot-plugin-design-builder/badge/"></a>
  <a href="https://pypi.org/project/design-builder/"><img src="https://img.shields.io/pypi/v/design-builder"></a>
  <a href="https://pypi.org/project/design-builder/"><img src="https://img.shields.io/pypi/dm/design-builder"></a>
  <br>
  An <a href="https://www.networktocode.com/nautobot/apps/">App</a> for <a href="https://nautobot.com/">Nautobot</a>.
</p>

## Overview

Design Builder is a Nautobot application for easily populating data within Nautobot using standardized design files. These design files are just Jinja templates that describe the Nautobot objects to be created or updated.

### Screenshots

> Developer Note: Add any representative screenshots of the App in action. These images should also be added to the `docs/user/app_use_cases.md` section.

> Developer Note: Place the files in the `docs/images/` folder and link them using only full URLs from GitHub, for example: `![Overview](https://raw.githubusercontent.com/networktocode-llc/nautobot-plugin-design-builder/develop/docs/images/plugin-overview.png)`. This absolute static linking is required to ensure the README renders properly in GitHub, the docs site, and any other external sites like PyPI.

More screenshots can be found in the [Using the App](https://docs.nautobot.com/projects/design-builder/en/latest/user/app_use_cases/) page in the documentation. Here's a quick overview of some of the plugin's added functionality:

![](https://raw.githubusercontent.com/networktocode-llc/nautobot-plugin-design-builder/develop/docs/images/placeholder.png)

## Documentation

Full documentation for this App can be found over on the [Nautobot Docs](https://docs.nautobot.com) website:

- [User Guide](user/app_overview.md) - Overview, Using the App, Getting Started.
- [Administrator Guide](admin/install.md) - How to Install, Configure, Upgrade, or Uninstall the App.
- [Developer Guide](docs/dev/contributing.md) - Extending the App, Code Reference, Contribution Guide.
- [Release Notes / Changelog](docs/admin/release_notes.md).
- [Frequently Asked Questions](docs/user/faq.md).

### Contributing to the Documentation

You can find all the Markdown source for the App documentation under the [`docs`](https://github.com/networktocode-llc/nautobot-plugin-design-builder/tree/develop/docs) folder in this repository. For simple edits, a Markdown capable editor is sufficient: clone the repository and edit away.

If you need to view the fully-generated documentation site, you can build it with [MkDocs](https://www.mkdocs.org/). A container hosting the documentation can be started using the `invoke` commands (details in the [Development Environment Guide](https://docs.nautobot.com/projects/design-builder/en/latest/dev/dev_environment/#docker-development-environment)) on [http://localhost:8001](http://localhost:8001). Using this container, as your changes to the documentation are saved, they will be automatically rebuilt and any pages currently being viewed will be reloaded in your browser.

Any PRs with fixes or improvements are very welcome!

## Questions

For any questions or comments, please check the [FAQ](https://docs.nautobot.com/projects/design-builder/en/latest/user/faq/) first. Feel free to also swing by the [Network to Code Slack](https://networktocode.slack.com/) (channel `#nautobot`), sign up [here](http://slack.networktocode.com/) if you don't have an account.
