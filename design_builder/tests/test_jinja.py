"""Unit tests related to jinja2 rendering in the Design Builder."""
import unittest

from design_builder.context import Context
from design_builder.jinja2 import new_template_environment


class TestJinja(unittest.TestCase):
    """Test jinja2 rendering with the custom context."""

    def test_indent(self):
        env = new_template_environment({})
        want = "\n    - foo\n      bar\n"
        got = env.from_string("\n    - {%indent%}foo\nbar{%endindent%}").render()
        self.assertEqual(want, got)

    def test_list_indent(self):
        env = new_template_environment({})
        items = ["foo1", "foo2", "foo3"]
        want = "\n    - foo1\n\n    - foo2\n\n    - foo3\n\n"
        template = "\n{% for item in items %}\n    - {%+ indent%}{{ item }}{%endindent +%}\n{%endfor%}\n"
        got = env.from_string(template).render({"items": items})
        self.assertEqual(want, got)

    def test_dict_indent(self):
        env = new_template_environment({})
        items = {"foo1": 1, "foo2": 2, "foo3": 3}
        want = "    - foo1: 1\n      foo2: 2\n      foo3: 3\n\n"
        template = "{% for item in items %}\n    - {%+ indent%}{{ item | to_yaml }}{%endindent%}\n{%endfor%}"
        got = env.from_string(template).render({"items": [items]})
        self.assertEqual(want, got)

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
        ]

        for test_case in test_cases:
            with self.subTest(test_case["name"]):
                env = new_template_environment(test_case["input"])
                template = env.from_string(test_case["template"])
                got = template.render()
                self.assertEqual(test_case["want"], got)
