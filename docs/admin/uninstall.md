# Uninstall the App from Nautobot

Here you will find any steps necessary to cleanly remove the App from your Nautobot environment.

## Uninstall Guide

Remove the `DESIN_BUILDER` section that was added to `nautobot_config.py` `PLUGINS` & `PLUGINS_CONFIG`.

## Database Cleanup

The current version of Design Builder does not include any database models, so no database cleanup is necessary.
