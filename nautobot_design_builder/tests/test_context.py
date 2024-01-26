"""Test jinja2 render context."""
import unittest

from nautobot_design_builder.context import Context, _DictNode
from nautobot_design_builder.tests.designs.context import BaseContext
from nautobot_design_builder.tests.designs.sub_designs import SubDesignContext


class TestContext(unittest.TestCase):
    """Test context."""

    def test_load(self):
        data = {"var1": "val1", "var2": "val2"}
        context = Context.load(data)
        self.assertEqual("val1", context.var1)
        self.assertEqual("val2", context.var2)

    def test_resolve(self):
        data = {"var1": "val1", "var2": "{{ var1 }}"}
        context = Context.load(data)
        self.assertEqual("val1", context.var1)
        self.assertEqual("val1", context.var2)

    def test_nested_resolve(self):
        data = {"var1": {"var3": "val3"}, "var2": "{{ var1.var3 }}"}
        context = Context.load(data)
        self.assertEqual("val3", context.var2)

    def test_properties(self):
        class PropertiesTest(Context):
            """Test class for context."""

            @property
            def my_prop(self):
                """Simple property for the context."""
                return "my_prop_value"

        data = {"var1": {"var3": "{{ my_prop }}"}, "var2": "{{ var1.var3 }}"}
        context = PropertiesTest.load(data)
        self.assertEqual("my_prop_value", context.var2)

    def test_update(self):
        data1 = {"var1": {"var4": "val4", "var3": "val3"}, "var2": "{{ var1.var3 }}"}

        data2 = {"var1": {"var3": "val5"}, "var3": "val33"}

        context = Context.load(data1)
        context.update(data2)
        self.assertEqual("val4", context.var1["var4"])
        self.assertEqual("val5", context.var1["var3"])
        self.assertEqual("val5", context["var2"])
        self.assertEqual("val33", context.var3)

    def test_nested_list(self):
        context = Context.load({"var1": {"var2": [True]}})
        self.assertTrue(context.var1["var2"][0])


class TestUpdateDictNode(unittest.TestCase):
    """Test dict node."""

    def test_simple_update(self):
        data1 = {"var1": "val1"}
        data2 = {"var1": "val2"}
        want = {"var1": "val2"}

        got = _DictNode(data1)
        got.update(data2)
        self.assertEqual(want, got)

    def test_templated_update(self):
        data1 = {
            "var1": "val1",
            "var2": "val2",
        }

        data2 = {
            "var3": "{{ var1 }}",
        }

        want = {
            "var1": "val1",
            "var2": "val2",
            "var3": "val1",
        }

        got = _DictNode(data1)
        got.update(data2)
        self.assertEqual(want, got)

    def test_nested_update(self):
        data1 = {
            "var1": {
                "var2": "val12",
                "var3": "val13",
            },
            "var2": "val2",
        }

        data2 = {
            "var1": {
                "var2": "{{ var2 }}",
            },
            "var3": "foo",
        }

        want = {
            "var1": {"var2": "val2", "var3": "val13"},
            "var2": "val2",
            "var3": "foo",
        }

        got = _DictNode(data1)
        got.update(data2)
        self.assertEqual(want, got)


class TestRootNode(unittest.TestCase):
    """Test root node."""

    def test_simple_struct(self):
        data = {"var1": "val1"}
        want = {"var1": "val1"}
        self.assertEqual(want, _DictNode(data))

    def test_different_structs(self):
        data = {"var1": "val1"}
        want = {"var1": "val2"}
        self.assertNotEqual(want, _DictNode(data))

    def test_nested_structs(self):
        data = {
            "var1": "val1",
            "var2": {
                "var1": True,
                "var2": False,
                "var3": "Foo",
            },
        }

        want = {"var1": "val1", "var2": {"var1": True, "var2": False, "var3": "Foo"}}
        self.assertEqual(want, _DictNode(data))

    def test_different_nested_structs(self):
        data = {
            "var1": "val1",
            "var2": {
                "var1": True,
                "var2": False,
                "var3": "Foo",
            },
        }

        want = {"var1": "val1", "var2": {"var1": True, "var2": True, "var3": "Foo"}}
        self.assertNotEqual(want, _DictNode(data))

    def test_simple_template_var(self):
        data = {"var1": "val1", "var2": "{{ var1 }}"}

        want = {"var1": "val1", "var2": "val1"}
        self.assertEqual(want, _DictNode(data))

    def test_nested_template_var(self):
        data = {
            "var1": {
                "var2": "val1",
            },
            "var3": {"var4": "{{ var1.var2 }}"},
        }

        want = {
            "var1": {
                "var2": "val1",
            },
            "var3": {"var4": "val1"},
        }
        self.assertEqual(want, _DictNode(data))

    def test_simple_lists(self):
        data = {"var1": ["one", "two", "three"]}
        want = {"var1": ["one", "two", "three"]}
        got = _DictNode(data)
        self.assertEqual(want, got)

    def test_list_with_template(self):
        data = {"var2": "{{ var1 }}", "var1": ["one", "two", "three"]}
        want = {"var2": ["one", "two", "three"], "var1": ["one", "two", "three"]}
        got = _DictNode(data)
        self.assertEqual(want, got)

    def test_list_with_differences(self):
        data = {"var2": "{{ var1 }}", "var1": ["one", "two", "three"]}
        want = {"var2": ["one", "two", "three"], "var1": ["one", "three"]}
        self.assertNotEqual(want, _DictNode(data))

    def test_complex_template_lookup(self):
        data = {
            "var1": {
                "var2": "{{ var3 }}",
            },
            "var3": "{{ var4 }}",
            "var4": "val4",
        }

        node = _DictNode(data)
        got = node["var1"]["var2"]
        self.assertEqual("val4", got)

    def test_something_other_than_a_string(self):
        data = {
            "var1": {"var2": "{{ var3 }}", "var3": True, "var4": 3.14159},
            "var3": "{{ var4 }}",
            "var4": 12345,
            "var5": "{{ var1.var3 }}",
            "var6": "{{ var1.var4 }}",
        }

        want = {
            "var1": {"var2": 12345, "var3": True, "var4": 3.14159},
            "var3": 12345,
            "var4": 12345,
            "var5": True,
            "var6": 3.14159,
        }

        got = _DictNode(data)
        self.assertEqual(want, got)


class TestContextDecorator(unittest.TestCase):
    """Test context decorator."""

    def test_context_file(self):
        base_files = [
            (BaseContext, "base_context_file"),
        ]

        sub_design_files = [
            (BaseContext, "base_context_file"),
            (SubDesignContext, "sub_design_context_file"),
        ]
        self.assertEqual(base_files, BaseContext.base_context_files())
        self.assertEqual(sub_design_files, SubDesignContext.base_context_files())
