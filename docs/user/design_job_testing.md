# Design Job Testing Framework

The Design Testing Framework allows for low-level testing of designs, but not a full `DesignJob`. Understanding the checks reviewed in the [prior section](./design_testing.md) is essential, as the classes we will review work with `DesignJob`.

## Quick Start

While `DesignTestCase` contains all core functionality, `VerifyDesignTestCase` offers a more user-friendly interface. This Quick Start demonstrates how to set it up.

In a unittest file, such as `test_design_jobs.py`, you can add the following code with your appropriate settings:

```python
class TestVerifyDesignJob(VerifyDesignTestCase):
    """Test running verify design jobs."""

    job_design = test_designs.VerifyDesign
    check_file = os.path.join(os.path.dirname(__file__), "checks", "verify_design.yaml")
    job_data = {"additional_manufacturer_1": "Manufacturer From Data"}

    def test_my_design(self):
        self.run_design_test()
```

The advantage of this solution is that the `check_file` uses the same check system introduced in the Test Design framework.

## VerifyDesignTestCase Overview

While the hard work, such as monkey patching various methods, happens in `DesignTestCase`, the `VerifyDesignTestCase` is intended to orchestrate the most common use case: kicking off a DesignJob with specific data and verifying it with the [check system](./design_testing.md#validating-data-with-checks).

There are three attributes that must be filled out:

- `job_design`: The design you are testing.
- `check_file`: The file with the definition of the checks in YAML format.
- `job_data`: The data you are sending in the Job Form. Set this to `{}` if there is no data to be sent.

Additionally, you need to call the `run_design_test` method from a `test_*` method, as shown in the Quick Start.

### Checks

Refer to the [Design Testing framework](./design_testing.md#validating-data-with-checks) for detailed information on how checks work and are defined.

## DesignTestCase Overview

The `DesignTestCase` is lower level and allows for additional testing as needed. It handles all the setup, monkey patching, etc., which is fairly involved.

Here is a quick example:

```python
class TestDesignJob(DesignTestCase):
    """Test running design jobs."""

    def test_simple_design_rollback(self):
        job1 = self.get_mocked_job(test_designs.SimpleDesign)
        job1.run(data={}, dryrun=False)
        self.assertEqual(2, Manufacturer.objects.all().count())
        job2 = self.get_mocked_job(test_designs.SimpleDesign3)
        self.assertRaises(DesignValidationError, job2.run, data={}, dryrun=False)
        self.assertEqual(2, Manufacturer.objects.all().count())
```

As per unittest standards, name your method `test_*` so it gets picked up by unittest. Outside of that, it is simply a standard Python test.
