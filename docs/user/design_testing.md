# Design Testing

Design Builder brings the higher responsibility for intended data generation to the design. The user's input data will tailor each deployment, but everything is done within the guardrails of the design. Thus, the designs **should** be tested properly on a continuous integration to ensure that they are behaving as expected.

This means that if the design is only for ad-hoc deployments (i.e., not tracked), at least the expected output should be validated for a few input data sets. If the design is implementing the lifecycle, then the tests should include the update and decommissioning features to grant that it will behave as expected.

## Design Unit Tests

Design Builder comes with a `DesignTestCase` utility class to let you get started. First you can customize a base `ExampleTestBase` class that you can reuse across many designs, to run jobs (i.e., `DesingJobs`) and assert the outputs.

```python
from nautobot_design_builder.tests import DesignTestCase
from ..base_data import LocalTestData

class ExampleTestBase(DesignTestCase):
    @classmethod
    def setUpClass(cls):
        """Run some base designs to generate data required for your designs."""
        super().setUpClass()
        for setup_job_class in [LocalTestData, ]:
            job = cls.get_mocked_job(cls, setup_job_class)
            job.run(data={}, commit=True)
            if job.failed:
                raise Exception(cls.logged_messages[-1])

    def setUp(self):
        super().setUp()
        # Add more data to all your tests
        self.region = Region.objects.get(name="East")

    def run_job(self, job_class, data=None):
        """Utility run job with some data."""
        if data is None:
            data = {}
        job = self.get_mocked_job(job_class)
        job_context = None

        def post_implementation(context, builder):
            nonlocal job_context
            job_context = context

        job.post_implementation = post_implementation
        job.run(data=data, commit=True)
        if job.failed:
            self.fail(self.logged_messages[-1]["message"])
        return job, job_context

```

Then, for each specific `Design`, you inherit from the previous utility class and customize it using our designs. In concrete, the workflow should be something like:

1. Import your `DesignJob` and `Context`
2. Define the test **Input Data**
3. Run the `DesignJob` using the `self.run_job` utility from above
4. Check with asserts if the expected data has been generated/updated

```python
from ..context import EdgeSiteBlocksContext
from ..jobs import ProvisionEdgeBlocksSite

class TestSiteDesign(DesignTestCase):
    def create_edge_site(self, site_code, **choices) -> Tuple[ProvisionEdgeBlocksSite, EdgeSiteBlocksContext]:
        """Helper function to create a site with this Job."""
        return self.run_job(
            ProvisionEdgeBlocksSite,
            data={
                "site_code": site_code,
                "region": self.region,
                "timezone": "US/Eastern",
                "transport_choice": Provider.objects.filter(id__isnull=True),
            },
        )

    def test_create_site(self):
        """Check that the Site is created."""
        sdwan_choice = DeviceType.objects.filter(tags__name="Core SDWAN").first()

        self.create_edge_site("SITE", sdwan_choice=sdwan_choice)
        self.assertEqual(1, Site.objects.all().count())
```

> For the update functionality (in the DEPLOYMENT mode), you can run the `DesignJob` many times and check it.

### Decommissioning Tests

If your `DesignJob` support the `DEPLOYMENT` mode, you should also test the decommissioning feature to validate that the data is reverted to its previous state.

You can validate if importing the `DeploymentDecommissioning` and run it pointing to your deployment. So, you reuse the previous logic to run the design, and then decommission it to check the final status.

```python
from nautobot_design_builder.jobs import DeploymentDecommissioning

class DecommissioningTestBase(DesignTestCase):
    def setUp(self):
        super().setUp()
        self.decommissioning_job = self.get_mocked_job(DeploymentDecommissioning)
        ...

```

### Test Context Functions

Context test functions can also be tested to validate that the logic works as expected.

```python
class TestEdgeSiteBlocksContext(DesignTestCase):
    def test_calculate_prefix(self):
        site = Site.objects.create(
            name="TEST SITE",
            status=Status.objects.get(name="Active"),
        )
        prefix = site.prefixes.create(
            prefix="192.0.2.0/24",
            status=Status.objects.get(name="Active"),
        )
        prefix.tags.add(Tag.objects.get(name="abc"))
        prefix.save()
        context = EdgeSiteBlocksContext({"site_code": "TEST SITE"})
        prefix_str = context.calculate_prefix({"parent": "abc", "offset": "0.0.0.0/28"})
        self.assertEqual("192.0.2.0/28", prefix_str)
```
