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
