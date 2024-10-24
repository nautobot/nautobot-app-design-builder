"""Unit tests related to jinja2 rendering in the Design Builder."""

import unittest

from nautobot_design_builder.context import Context
from nautobot_design_builder.jinja2 import new_template_environment


class TestJinja(unittest.TestCase):
    """Test jinja2 rendering with the custom context."""

    def test_simple_render(self):
        data = {"var1": "val1", "var2": "val2"}
        context = Context.load(data)
        env = new_template_environment(context)
        want = "val1"
        got = env.from_string(r"{{ var1 }}").render()
        self.assertEqual(want, got)

    def test_context_with_property(self):
        class TestContext(Context):  # pylint:disable=missing-class-docstring
            @property
            def name(self):  # pylint:disable=missing-function-docstring
                return "Test Name"

        env = new_template_environment(TestContext())
        want = "Test Name"
        got = env.from_string(r"{{ name }}").render()
        self.assertEqual(want, got)

    def test_context_with_nested_property(self):
        class Name:  # pylint:disable=missing-class-docstring,too-few-public-methods
            @property
            def name(self):  # pylint:disable=missing-function-docstring
                return "Test Name"

        class TestContext(Context):  # pylint:disable=missing-class-docstring
            def __init__(self):
                super().__init__()
                self._parent = Name()

            @property
            def parent(self):  # pylint:disable=missing-function-docstring
                return self._parent

        env = new_template_environment(TestContext())
        want = "Test Name"
        got = env.from_string(r"{{ parent.name }}").render()
        self.assertEqual(want, got)

    def test_to_yaml(self):
        test_cases = [
            {
                "name": "base context",
                "input": Context.load({"name": "name", "value": "value"}),
                "template": "{{ context | to_yaml }}",
                "want": "name: name\nvalue: value\n",
            },
            {
                "name": "base context",
                "input": Context.load({"name": {"value": "value"}}),
                "template": "{{ context.name | to_yaml }}",
                "want": "value: value\n",
            },
            {
                "name": "weird float values",
                "want": """latitude: 35.350498199499995
longitude: -116.888000488
name: 00CA - Goldstone /Gts/ Airport
region__slug: region-us-ca
slug: 00ca
tenant__slug: small-sites
""",
                "template": "{{ context.sites[0] | to_yaml }}",
                "input": Context.load(
                    {
                        "sites": [
                            {
                                "latitude": "35.350498199499995",
                                "longitude": "-116.888000488",
                                "name": "00CA - Goldstone /Gts/ Airport",
                                "region__slug": "region-us-ca",
                                "slug": "00ca",
                                "tenant__slug": "small-sites",
                            },
                        ],
                    }
                ),
            },
            {
                "name": "Lists",
                "input": Context.load(
                    {"device_type": {"interfacetemplates": [{"name": "Network", "type": "100base-t"}]}}
                ),
                "template": "{{ context.device_type | to_yaml }}",
                "want": """interfacetemplates:
- name: Network
  type: 100base-t
""",
            },
        ]

        for test_case in test_cases:
            with self.subTest(test_case["name"]):
                env = new_template_environment(test_case["input"])
                template = env.from_string(test_case["template"])
                got = template.render()
                self.assertEqual(test_case["want"], got)
