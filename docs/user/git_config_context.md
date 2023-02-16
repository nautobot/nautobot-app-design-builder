# Git-based Config Context

Design Builder is capable of generating config contexts for devices based on Jinja templates. The config contexts can either be stored directly in the Nautobot database, or they can be added to a config context git repository. This document covers storing the generated config contexts in a git repository.

More background information on config contexts can be found in the [official Nautobot documentation](https://nautobot.readthedocs.io/en/latest/additional-features/config-contexts/).

Before this capability can be used, Nautobot must be configured with a Git repository set to include `Config Contexts` (see the [official documentation](https://nautobot.readthedocs.io/en/stable/models/extras/gitrepository/)).

Additionally, the design builder needs to be configured for Git contexts. In order to configure design_builder update `PLUGIN_CONFIG` in `nautobot_config.py` and set the `context_repository` configuration setting to the `slug` of the configured context repository:

```python
PLUGINS_CONFIG = {
    "design_builder": {
        "context_repository": "slug-of-the-git-repo"
    }
}
```
