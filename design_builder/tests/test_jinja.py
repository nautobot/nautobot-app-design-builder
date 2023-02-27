"""Unit tests related to jinja2 rendering in the Design Builder."""
import unittest

from design_builder.context import Context
from design_builder.jinja2 import new_template_environment


class TestJinja(unittest.TestCase):
    """Test jinja2 rendering with the custom context."""

    def test_simple_render(self):
        data = {"var1": "val1", "var2": "val2"}
        context = Context.load(data)
        env = new_template_environment(context)
        want = "val1"
        got = env.from_string(r"{{ var1 }}").render()
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
        ]

        for test_case in test_cases:
            with self.subTest(test_case["name"]):
                env = new_template_environment(test_case["input"])
                template = env.from_string(test_case["template"])
                got = template.render()
                self.assertEqual(test_case["want"], got)
