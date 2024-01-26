# Upgrading the App

Here you will find any steps necessary to upgrade the App in your Nautobot environment.

## Upgrade Guide

Since Design Builder does not currently include any custom data models the only requirement for updating is to update the `nautobot-design-builder` package using the `pip` command:

```python
pip install --upgrade nautobot-design-builder
```

When a new release comes out it may be necessary to run a migration of the database to account for any changes in the data models used by this plugin. Execute the command `nautobot-server post-upgrade` within the runtime environment of your Nautobot installation after updating the `nautobot-design-builder` package via `pip`.
