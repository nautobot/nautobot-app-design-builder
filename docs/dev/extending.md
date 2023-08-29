# Extending the App

Design builder is primarily extended by creating new action tags. These action tags can be provided by a design repository or they can be contributed to the upstream Design Builder project for consumption by the community. Upstreaming these extensions is welcome, however it is best to open an issue first, to ensure that a PR would be accepted and makes sense in terms of features and design.

## Action Tag Extensions

The action tags in Design Builder are provided by `design.Builder`. This component reads a design and then executes instructions that are specified in the design. Basic functions, provided out of the box, are
`create`, `create_or_update` and `update`. These actions are self explanatory (for details on syntax see [this document](../user//design_development.md#special-syntax)). Two additional actions are provided, these are the `ref` and `git_context` actions. These two actions are provided as extensions to the builder.

Extensions specify attribute and/or value actions to the object creator. Within a design template, these extensions can be used by specifying an exclamation point (!) followed by the extensions attribute or value tag. For instance, the `ref` extension implements both an attribute and a value extension. This extension can be used by specifying `!ref`. Extensions can add behavior to the object creator that is not supplied by the standard create and update actions.

### Attribute Extensions

Attribute extensions provide some functionality when specified as a YAMl attribute. For instance:

```yaml
devices:
    name: My New Device
    "!my_attribute_extension": "some data passed to the extensions"
```

In this case, when the object creator encountered `!my_attribute_extension` it will look for an extension that specifies an attribute_tag `my_attribute_extension` and will call the associated `attribute` method on that extension. The `attribute` method will be given the object that is being worked on (the device "My New Device" in this case) as well as the value assigned to the attribute (the string "some data ..." in this case). Values can be any supported YAML type including strings, dictionaries and lists. It is up to the extension to determine if the provided value is valid or not.

### Value Extensions

Value extensions can be used to assign a value to an attribute. For instance:

```yaml
device:
    name: "!device_name"
```

In this case, when `!device_name` is encountered the object creator will look for an extension that implements the `device_name` value tag. If found, the corresponding `value` method will be called on the extension. Whatever `value` returns will be assigned to the attribute (`name` in this case). For a concrete example of an extension that implements both `attribute` and `value` see the [API docs](../api/ext.md#design_builder.ext.ReferenceExtension) for the ReferenceExtension.

### Writing a New Extension

Adding functionality to `design.Builder` is as simple extending the [Extension](../api/ext.md#design_builder.ext.Extension) class and supplying `attribute_tag` and/or `value_tag` class variables as well as the corresponding `attribute` and `value` instance methods. Extensions are singletons within a Builder instance. When an extension's tag is encountered an instance of the extension is created. Subsequent calls to the extension will use the instance created the first time.

Each extension may optionally implement `commit` or `roll_back` methods. The `commit` method is called once all of a design's objects have been created and updated in the database. Conversely, `roll_back` is called if any error occurs and the database transaction is aborted. These methods provide a means for an extension to perform additional work, or cleanup, based on the outcome of a design's database actions.
