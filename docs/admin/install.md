# Installing the App in Nautobot

Here you will find detailed instructions on how to **install** and **configure** the App within your Nautobot environment.

## Prerequisites

- The plugin is compatible with Nautobot 1.6.0 and higher.
- Databases supported: PostgreSQL, MySQL

!!! note
    Please check the [dedicated page](compatibility_matrix.md) for a full compatibility matrix and the deprecation policy.

### Access Requirements

Design Builder does not necessarily require any external system access. However, if design jobs will be loaded from a git repository, then the Nautobot instances will need access to the git repo.

## Install Guide

!!! note
    Plugins can be installed manually or using Python's `pip`. See the [nautobot documentation](https://nautobot.readthedocs.io/en/latest/plugins/#install-the-package) for more details. The pip package name for this plugin is [`nautobot-design-builder`](https://pypi.org/project/nautobot-design-builder/).

The plugin is available as a Python package via PyPI and can be installed with `pip`:

```shell
pip install nautobot-design-builder
```

To ensure Nautobot Design Builder is automatically re-installed during future upgrades, create a file named `local_requirements.txt` (if not already existing) in the Nautobot root directory (alongside `requirements.txt`) and list the `nautobot-design-builder` package:

```shell
echo nautobot-design-builder >> local_requirements.txt
```

Once installed, the plugin needs to be enabled in your Nautobot configuration. The following block of code below shows the additional configuration required to be added to your `nautobot_config.py` file:

- Append `"nautobot_design_builder"` to the `PLUGINS` list.
- Append the `"nautobot_design_builder"` dictionary to the `PLUGINS_CONFIG` dictionary and override any defaults.

```python
# In your nautobot_config.py
PLUGINS = ["nautobot_design_builder"]

# PLUGINS_CONFIG = {
#   "nautobot_design_builder": {
#     ADD YOUR SETTINGS HERE
#   }
# }
```

### Data Protection

Data protection allows enforcing consistent protection of data owned by designs.

There are two data protection configuration settings, and this is how you can manage them.

#### Define the Protected Data Models

By default, no data models are protected. To enable data protection, you should add it under the `PLUGINS_CONFIG`:

```python
PLUGINS_CONFIG = {
    "nautobot_design_builder": {
        "protected_models": [("dcim", "location"), ("dcim", "device")],
        ...
    }
}
```

In this example, data protection feature will be only taken into account for locations and devices.

#### Bypass Data Protection for Super Users

First, you have to enable a middleware that provides request information in all the Django processing.

```python
MIDDLEWARE.insert(0, "nautobot_design_builder.middleware.GlobalRequestMiddleware")
```

Finally, you have to tune the default behavior of allowing superuser bypass of protection (i.e., `True`).

```python
PLUGINS_CONFIG = {
    "nautobot_design_builder": {
        "protected_superuser_bypass": False,
        ...
    }
}
```

Once the Nautobot configuration is updated, run the Post Upgrade command (`nautobot-server post_upgrade`) to run migrations and clear any cache:

```shell
nautobot-server post_upgrade
```

Then restart (if necessary) the Nautobot services which may include:

- Nautobot
- Nautobot Workers
- Nautobot Scheduler

```shell
sudo systemctl restart nautobot nautobot-worker nautobot-scheduler
```
