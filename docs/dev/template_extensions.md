# Design Template Extensions

The action tags in Design Builder are provided by `design.Builder`. This component reads a design and then executes instructions that are specified in the design. Basic functions, provided out of the box, are
`create`, `create_or_update` and `update`. These actions are self explanatory (for details on syntax see [this document](../user//design_development.md#special-syntax)). Two additional actions are provided, these are the `ref` and `git_context` actions. These two actions are provided as extensions to the object creator.

Extensions specify attribute and/or value actions to the object creator. Within a design template, these extensions can be used by specifying an exclamation point (!) followed by the extensions attribute or value tag. For instance, the `ref` extension implements both an attribute and a value extension. This extension can be used by specifying `!ref`. Extensions can add behavior to the object creator that is not supplied by the standard create and update actions.

## Attribute Extensions

Attribute extensions provide some functionality when specified as a YAMl attribute. For instance:

```yaml
devices:
    name: My New Device
    "!my_attribute_extension": "some data passed to the extensions"
```

In this case, when the object creator encountered `!my_attribute_extension` it will look for an extension that specifies an attribute_tag `my_attribute_extension` and will call the associated `attribute` method on that extension. The `attribute` method will be given the object that is being worked on (the device "My New Device" in this case) as well as the value assigned to the attribute (the string "some data ..." in this case). Values can be any supported YAML type including strings, dictionaries and lists. It is up to the extension to determine if the provided value is valid or not.

## Value Extensions

Value extensions can be used to assign a value to an attribute. For instance:

```yaml
device:
    name: "!device_name"
```

In this case, when `!device_name` is encountered the object creator will look for an extension that implements the `device_name` value tag. If found, the corresponding `value` method will be called on the extension. Whatever `value` returns will be assigned to the attribute (`name` in this case). For a concrete example of an extension that implements both `attribute` and `value` see the [API docs](../api/ext.md#design_builder.ext.ReferenceExtension) for the ReferenceExtension.

## Writing a New Extension

Adding functionality to Object Creator is as simple extending the [Extension](../api/ext.md#design_builder.ext.Extension) class and supplying `attribute_tag` and/or `value_tag` class variables as well as the corresponding `attribute` and `value` instance methods. The ObjectCreator [constructor](../api/object_creator.md#design_builder.object_creator.ObjectCreator.__init__) will also need to be updated to add the new extension class. Only one instance of each extension is created and it is created when the first matching attribute or value tag is encountered.

Each extension may optionally implement `commit` or `roll_back` methods. The `commit` method is called once all of a design's opjects have been created and updated in the database. Conversely, `roll_back` is called if any error occurs and the database transaction is aborted. These methods provide a means for an extension to perform additional work, or cleanup, based on the outcome of a design's database actions.
