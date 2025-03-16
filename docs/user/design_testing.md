# Design Testing Framework

## Overview

The Nautobot Design Builder testing framework streamlines and standardizes the process of testing within your designs by leveraging YAML files to create data objects and verify their consistency. This ensures no regressions in your design builds as both your designs and the Nautobot Design Builder evolve.

The Nautobot Design Builder testing framework provides:

- **Data Creation**: Tools to easily create and configure test data, such as devices, prefixes, and any object.
- **Data Validation**: Various "check" methods to verify that the data and application state meet the expected conditions.
- **Modular Design**: Extension and customization of the framework to fit specific testing needs.

## Quick Start

To get started with the Nautobot Design Builder testing framework, create a simple YAML file to define a device and set up a test to verify its creation.

Create a file named `ensure_device.yaml` in your `tests/testdata/` folder with the following content:

```yaml
devices:
  - name: Test Device
    device_type: Test Type
    device_role: Test Role
    site: Test Site
checks:
  - model_exists:
      model: dcim.device
      name: Test Device
```

In your test file, such as `test_builder.py` or `unittest/test_builder.py`, use the following code to verify the device creation:

```python
from nautobot_design_builder.testing import BuilderTestCase

class TestGeneralDesigns(BuilderTestCase):
    """Designs that should work with all versions of Nautobot."""

    data_dir = os.path.join(os.path.dirname(__file__), "testdata")
```

This should be enough to get you started and infer how the system works. Essentially, you create designs and then check that the results are as expected.

> Note: While you can set the `testdata` folder to be anything, we will refer to it as `tests/testdata/` throughout the documentation.

## Unittest Setup

Most of the setup was provided in the Quick Start. For completeness, here is how you would set up your unittest. In your test file, such as `test_builder.py` or `unittest/test_builder.py`, use the following code to verify the device creation:

```python
from nautobot_design_builder.testing import BuilderTestCase

class TestGeneralDesigns(BuilderTestCase):
    """Designs that should work with all versions of Nautobot."""

    data_dir = os.path.join(os.path.dirname(__file__), "testdata")
```

The `data_dir` folder can be any valid folder. The code provided essentially says "from the folder called `testdata` relative to my file". You can have multiple classes inherit from `BuilderTestCase` and leverage different folders, such as `TestBranchDesigns(BuilderTestCase)` and `TestColoDesigns(BuilderTestCase)` pointing to different folders.

> Note: Unittest and CI setup is beyond the scope of this documentation.

## Create Data

To create a design, you create a list of designs. While often there will be a single design, there is support for running through multiple designs.

Let's say you have the design called `base_design.yaml.j2` that looks like:

```yaml
manufacturers:
  - name: "cisco"
  - name: "arista"

device_types:
  - manufacturer__name: "cisco"
    model: "WS-C9300-12X-S"
    u_height: 1
```

That would become the file `base_design.yaml` in your `tests/testdata` folder:

```yaml
designs:
  - manufacturers:
      - name: "cisco"
      - name: "arista"

    device_types:
      - manufacturer__name: "cisco"
        model: "WS-C9300-12X-S"
        u_height: 1
```

You would tier the design under an element in the `designs:` key. You can have multiple designs, such as:

```yaml
designs:
  - manufacturers:
      - name: "cisco"
      - name: "arista"

    device_types:
      - manufacturer__name: "cisco"
        model: "WS-C9300-12X-S"
        u_height: 1

  - manufacturers: # Though simple, this is the second design
      - name: "palo alto"
```

This is how you declare multiple designs, as you re-initiate `manufacturers` in the second design.

### Data Reuse

The `depends_on` feature allows you to create complex designs by building upon existing ones. This is useful when you have a base design that multiple other designs need to extend or modify. By using the `depends_on` key, you can ensure that the base design is always applied before the dependent design, maintaining consistency and reducing redundant code.

To use `depends_on`, reference the base design in the dependent design's YAML file.

**Base Design**: Create a file named `base_design.yaml` in your `tests/testdata/` folder with the following content:

```yaml
designs:
  - manufacturers:
      - name: "cisco"
      - name: "arista"

    device_types:
      - manufacturer__name: "cisco"
        model: "WS-C9300-12X-S"
        u_height: 1
```

**Dependent Design**: Create another file named `branch_design.yaml` in the same folder with the following content:

```yaml
depends_on: base_design.yaml

designs:
  - devices:
      - name: "Test Device"
        device_type: "WS-C9300-12X-S"
        device_role: "Test Role"
        site: "Test Site"
```

In this example, `branch_design.yaml` depends on `base_design.yaml`. When `branch_design.yaml` is processed, it will first apply the configurations from `base_design.yaml` and then apply its own configurations. This ensures that the device type "WS-C9300-12X-S" defined in the base design is available when creating the "Test Device" in the extended design.

## Validating Data with Checks

The "check" methods in the Nautobot Design Builder testing framework validate that the data and application state meet the expected conditions. These checks help ensure that your designs are correctly implemented and that no regressions occur as your designs or the Nautobot Design Builder evolve.

Currently, we support the following checks:

- connected
- equal
- model_exists
- model_not_exist
- in
- not_in

We will go into more detail on them in the next sections.

There are two main types of responses you can get from your check, a model or a value:

- **Model**: This response type indicates that the check is verifying the existence or properties of a specific model instance. For example, the `model_exists` check ensures that a particular instance of a model, such as a device, exists in the database.
- **Value**: This response type indicates that the check is verifying a specific value or set of values within a model's field. For example, the `equal` check ensures that a field of a model equals a specific value, such as verifying that a device's name is "Test Device".

> Note: Model without using the `count` argument will return a list, so your value will often be a list of data.

By using these check systems, you can automate the validation process, reduce manual testing efforts, and maintain a high level of confidence in your design implementations.

### Value Response Type

The value response type is straightforward. This is simply the data you define, with no data manipulation or query run to get the data. In general, this will be used in checks when you are comparing data from a model.

```yaml
checks:
  - equal:
      - model: "nautobot.dcim.models.Device"
        query: {name: "test device"}
        attribute: "rack.name"
      - value: ["rack-1"]
```

This is saying that the `model` and `attribute` or `rack.name` will return exactly the `value` of `["rack-1"]`.

### Model Response Type

The model response type involves using the `model`, `query`, `attribute`, and `count` keys to define the checks.

- **model**: Specifies the model to query. This should be a string representing the full dotted path to the model class, e.g., `"nautobot.dcim.models.Device"`.
- **query**: (Optional) A dictionary that defines the conditions for the query, specifically a valid dictionary that would be accepted on a queryset to the Django model defined. This dictionary is used to filter the model instances based on the specified conditions and is valid, e.g., `{"name": "test device"}`.
- **attribute**: (Optional) Specifies the attribute of the model to check. This should be a string representing the attribute path, e.g., `"rack.name"`. If not provided, the check returns the full model instances as a list.
- **count**: (Optional) This is a boolean that defaults to not being set. Use `count: true` and be careful of how YAML will interpret values; you would be wise to omit the key if not setting it to `true`.

As mentioned, the model will return a list in all cases **except** when using count. It will either be a list of attributes or a list of models.

#### Example with Attribute

In this example, the check verifies that the `rack.name` attribute of a device with the name "test device" is equal to `["rack-1"]`:

```yaml
  - equal:
      - model: "nautobot.dcim.models.Device"
        query: {name: "test device"}
        attribute: "rack.name"
      - value: ["rack-1"]
```

#### Example without Attribute

In this example, the check verifies that a device with the name "test device" exists:

```yaml
checks:
  - model_exists:
      model: "nautobot.dcim.models.Device"
      query: {name: "test device"}
```

#### Example with Count

In this example, we are verifying that there are 2 model instances created.

```yaml
checks:
  - equal:
      - model: "nautobot.extras.models.Secret"
        count: true
      - value: 2
```

### Check Types

The checks generally compare two values, what is returned in the first item in the list compared to what is returned in the second item. However, you can also test if an object exists or does not exist with the `model_exists` and `model_not_exists` checks.

> Note: In addition to checks, there are `pre_checks`, which have all of the same rules as `checks`, but they happen before the design is run. This is helpful if you want to ensure something does not exist before your design and does exist after your design, as one example.

#### The connected Check

The `connected` check verifies that two interface objects are connected with a cable object. For example, to check if two devices are connected:

```yaml
checks:
  - connected:
      - model: "nautobot.dcim.models.Interface"
        query: {device__name: "Device 1", name: "GigabitEthernet1"}
      - model: "nautobot.dcim.models.Interface"
        query: {device__name: "Device 2", name: "GigabitEthernet1"}
```

This check type is a bit different from the other pattern, so pay close attention to how it is used.

#### The equal Check

The `equal` check verifies that a field of a model equals a specific value. For example, to check if a device's name is "Test Device":

In this example, we test that the model itself is the same.

```yaml
checks:
  - equal:
      - model: "nautobot.dcim.models.DeviceType"
        query: {model: "model1"}
        attribute: "manufacturer"
      - model: "nautobot.dcim.models.Manufacturer"
        query: {name: "Manufacturer1"}
```

In this example, we test that the value is the same as returned, and we use the count value to get the number of elements.

```yaml
checks:
  - equal:
      - model: "nautobot.extras.models.Secret"
        count: true
      - value: 2
```

#### The model_exists Check

The `model_exists` check verifies that an instance of a model exists. For example, to check if a prefix "10.0.0.0/24" exists:

```yaml
checks:
  - model_exists:
      model: "nautobot.ipam.models.Prefix"
      query: {prefix: "10.0.0.0/24"}
```

This is often good enough to ensure your design is working, so keep that in mind as you build your tests to not over-complicate them.

> Note: There is a single dictionary, not a list of dictionaries in `model_exists`.

#### The model_not_exist Check

The `model_not_exist` check verifies that an instance of a model does not exist. For example, to check if a device named "WS-C9300-12X-S" does not exist:

```yaml
checks:
  - model_not_exist:
      model: "nautobot.dcim.models.DeviceType"
      query: {model: "WS-C9300-12X-S"}
```

> Note: There is a single dictionary, not a list of dictionaries in `model_not_exist`.

#### The in Check

The `in` check verifies that a field of a model is in a specific list of values. For example, to check if the content types for Status are in the Content Types:

```yaml
checks:
  - in:
      - model: "django.contrib.contenttypes.models.ContentType"
        query: {app_label: "dcim", model: "cable"}
      - model: "nautobot.extras.models.Status"
        query: {name: "Active"}
        attribute: "content_types"
```

#### The not_in Check

The `not_in` check verifies that a field of a model is not in a specific list of values. For example, to check if the content types for Status are **not** in the Content Types:

```yaml
  - not_in:
      - model: "django.contrib.contenttypes.models.ContentType"
        query: {app_label: "dcim", model: "cable"}
      - model: "nautobot.extras.models.Status"
        query: {name: "Active"}
        attribute: "content_types"
```

## Extensions

Extensions need to be explicitly defined as they are not automatically loaded. This allows you to customize and extend the functionality of the Nautobot Design Builder testing framework to fit your specific needs.

To define an extension, include it in the `extensions` key in your YAML file. Here is an example:

```yaml
extensions:
  - "nautobot_design_builder.contrib.ext.NextPrefixExtension"
designs:
  - tenants:
      - name: "Nautobot Airports"
    roles:
      - name: "Video"
        content_types:
          - "!get:app_label": "ipam"
            "!get:model": "prefix"
      - name: "Servers"
        content_types:
          - "!get:app_label": "ipam"
            "!get:model": "prefix"
  - prefixes:
      - prefix: "10.0.0.0/23"
        status__name: "Active"
        tenant__name: "Nautobot Airports"
        role__name: "Servers"
      - prefix: "10.0.2.0/23"
        status__name: "Active"
        tenant__name: "Nautobot Airports"
        role__name: "Video"
      - "!next_prefix":
          prefix:
            - "10.0.0.0/23"
            - "10.0.2.0/23"
          length: 24
        status__name: "Active"
```

In this example, the `NextPrefixExtension` is explicitly defined in the `extensions` key. This extension will be loaded and used to process the `!next_prefix` directive in the `designs` section.

## Running Single Tests

Occasionally, you want to run a single test. In unittest, they have the concept of a label to run a single test. Here is an example of using the Python unittest with a label:

```shell
python -m nautobot.core.cli test nautobot_design_builder.tests.test_builder.TestGeneralDesigns --keepdb --buffer
```

This is generally easier to track, as the label is all real folders, files, and classes. However, the YAML file gets ingested, and the test name is auto-created. The name of the test will be the word `test_` and the root of the name (e.g., without the .yaml extension on it), such as `test_prefixes_for_location` for the file `prefixes_for_location.yaml`. Here is an example of running a single test with a label:

```shell
python -m nautobot.core.cli test nautobot_design_builder.tests.test_builder.TestGeneralDesigns.test_prefixes_for_location --keepdb --buffer
```

This is helpful if you do not want to run all of your tests while testing a single issue or working on the root issue first.
