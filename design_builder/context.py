"""Module that contains classes and functions for use with Design Builder context available when using Jinja templating."""
import inspect
from typing import Iterable

import yaml
from nautobot.extras.models import JobResult

from design_builder.errors import DesignValidationError
from design_builder.jinja2 import new_template_environment
from design_builder.logging import LoggingMixin
from design_builder.util import load_design_yaml


class _Node:
    _root: "_Node"

    def __init__(self, root: "_Node"):
        super().__init__()
        if root is None:
            root = self

        if root is self:
            self.env = new_template_environment(root, native_environment=True)
        self._root = root

    def _compare(self, subscripts, other):
        """Compare 'other' to the node's data store."""
        for i in subscripts:
            value = self.__getitem__(i)
            if value != other[i]:
                return False
        return True

    def __contains__(self, key):
        if hasattr(self, "_store"):
            return key in getattr(self, "_store")
        return False

    def __repr__(self):
        if hasattr(self, "_store"):
            return repr(getattr(self, "_store"))
        return super().__repr__()

    def __getitem__(self, item) -> "_Node":
        """Walk the context tree and return the value.

        This method contains the logic that will find a leaf node
        in a context tree and return its value. If the leaf node
        is a template, the template is rendered before being returned.
        """
        if isinstance(item, str) and hasattr(self, item):
            val = getattr(self, item)
        elif hasattr(self, "_store"):
            val = getattr(self, "_store")[item]
        else:
            raise KeyError(item)

        if isinstance(val, _TemplateNode):
            val = val.render()
        return val

    def _create_node(self, value):
        """Create a new node for the value.

        Args:
            value: a value that needs to be inserted into a parent node

        Returns:
            A new Node. If the value is a list then a new _ListNode is returned
            if the value is a dict then a new _DictNode, if the value is a string
            then a new _TemplateNode, otherwise the original value (a leaf node)
            is returned.
        """
        if isinstance(value, list):
            return _ListNode(self._root, value)

        if isinstance(value, dict):
            return _DictNode(self._root, value)

        if isinstance(value, str):
            return _TemplateNode(self._root, value)

        return value


class _TemplateNode(_Node):
    """A TemplateNode represents a string or jinja2 template value.

    Args:
        root: The root node to be used when looking up variables in the context tree
        tpl: a string template to be rendered at a later time
    """

    def __init__(self, root: _Node, tpl: str):
        super().__init__(root)
        self.update(tpl)

    def render(self) -> str:
        """Render the template node."""
        return self._template.render()

    def update(self, tpl: str):
        """Replace the template node template with the input argument.

        Args:
            tpl: the new template string
        """
        self._template = self._root.env.from_string(tpl)

    def __eq__(self, other):
        return self.__str__() == other

    def __hash__(self) -> int:
        return self.render().__hash__()

    def __repr__(self) -> str:
        return f"'{self.render()}'"

    def __str__(self) -> str:
        return str(self.render())


class _ListNode(_Node):
    """A _ListNode is a level in the context tree backed by a list store.

    Args:
        root: The root node for variable lookups.
        data: The data to be populated into this _ListNode.
    """

    def __init__(self, root: _Node, data: dict):
        super().__init__(root)
        self._store = []
        self.update(data)

    def update(self, data: list):
        """Merge the provided data with the current node."""
        if not isinstance(data, list):
            raise ValueError("ListNode can only be updated from a list")

        for i, item in enumerate(data):
            if i == len(self._store):
                self._store.append(self._create_node(item))
            elif isinstance(self._store[i], _Node):
                self._store[i].update(item)
            else:
                self._store[i] = self._root._create_node(item)  # pylint: disable=protected-access

    def __len__(self):
        return len(self._store)

    def __eq__(self, other: list):
        if len(self._store) != len(other):
            return False
        return self._compare(range(len(self._store)), other)


class _DictNode(_Node):
    """A _DictNode is a level in the context tree backed by a dictionary store.

    Args:
        root: The root node for variable lookups.
        data: The data to be populated into this _DictNode.
    """

    class DictNodeIterable:
        """Iterator for _DictNode."""

        def __init__(self, dict_node: "_DictNode"):
            self._dict_node = dict_node
            self._keys = iter(self._dict_node._store)

        def __iter__(self):
            return self

        def __next__(self):
            key = next(self._keys)
            return [key, self._dict_node[key]]

    def __init__(self, root: _Node, data: dict):
        super().__init__(root)
        self._store = {}
        self.update(data)

    def update(self, data: dict):
        """Merge the provided data with this node."""
        if not isinstance(data, dict):
            raise ValueError("DictNode can only be updated from a dict")

        for key, value in data.items():
            if key in self._store and isinstance(self._store[key], _Node):
                self._store[key].update(value)
            else:
                self._store[key] = self._root._create_node(value)  # pylint: disable=protected-access

    def keys(self) -> Iterable:
        """Return an iterable of the node's keys."""
        return self._store.keys()

    def values(self) -> Iterable:
        """Return an iterable of the node's values."""
        return self._store.values()

    def items(self) -> Iterable:
        """Return an iterable of the key/value pairs in this node."""
        return self.DictNodeIterable(self)

    def __eq__(self, other: dict):
        if self._store.keys() != other.keys():
            return False
        return self._compare(self._store.keys(), other)


def context_file(*ctx_files):
    """Add a context file to a class.

    Context Files are only loaded once per class hierarchy, even if they are
    specified more than once in a class/subclass tree. Context files must
    be in YAML format. Each context file will be loaded and parsed and
    merged together to form a base context.
    """

    def wrapper(context_cls):
        if "__base_contexts" not in context_cls.__dict__:
            setattr(context_cls, "__base_contexts", {})

        for ctx_file in ctx_files:
            base_context = getattr(context_cls, "__base_contexts")
            # only load each context file once
            if ctx_file not in base_context:
                data = load_design_yaml(context_cls, ctx_file)
                # don't add anything if the file was empty
                if data:
                    base_context[ctx_file] = data

        return context_cls

    return wrapper


class Context(_Node, LoggingMixin):
    """A context represents a tree of variables that can include templates for values.

    Context provides a way to inject variables into designs. Contexts can be loaded from
    YAML files or they can be defined as Python code or combinations of the two.  For
    Contexts that are loaded from YAML files, values can be jinja templates that are
    evaluated when looked up.  The jinja template can refer to other values within
    the context.  If a context loads multiple files then the files are merged and
    a template in one can refer to values assigned in another.

    Args:
        data: a dictionary of values to be loaded into the context. This dictionary
              will be recursively evaluated and each level will be stored as either
              a _DictNode or _ListNode. Leaves will be stored either as a _TemplateNode
              or their native type.
    """

    def __init__(self, data: dict = None, job_result: JobResult = None):
        """Constructor for Context class that creates data nodes from input data."""
        super().__init__(self)
        self._keys = []
        self.job_result = job_result

        # Copy the base contexts right into the
        # context instance to make it easier to
        # reference in the downstream design
        bases = list(inspect.getmro(type(self)))
        bases.reverse()

        for base in bases:
            for context in base.__dict__.get("__base_contexts", {}).values():
                self.update(context)

        if data is not None:
            for key, value in data.items():
                self._keys.append(key)
                setattr(self, key, self._create_node(value))

    @classmethod
    def base_context(cls):
        """The base context is the combination of any context_files that have been added to a context.

        Calling base_context will merge all of the context trees that have been added by the
        @context_file decorator.

        Returns:
            Merged context tree
        """
        base = Context()
        for context in getattr(cls, "__base_contexts", {}).values():
            base.update(context)
        return base

    @classmethod
    def load(cls, yaml_or_mapping):
        """Load a context from a yaml file or mapping."""
        if isinstance(yaml_or_mapping, dict):
            return cls(data=yaml_or_mapping)

        if isinstance(yaml_or_mapping, list):
            raise ValueError("Can only load mappings or yaml")

        return cls.load(yaml.safe_load(yaml_or_mapping))

    def validate(self):
        """Validate that the context can be used to render a design.

        This method will look for any method names that start with "validate_" and will
        call them successively.

        Raises:
            Any DesignValidationErrors raised by the validators will be collected. and a single
            DesignValidationError will be raised that includes all the error messages.
        """
        methods = [method for method in dir(self) if method.startswith("validate_") and callable(getattr(self, method))]
        errors = []
        for method in methods:
            try:
                getattr(self, method)()
            except DesignValidationError as ex:
                errors.append(str(ex))

        if len(errors) > 0:
            raise DesignValidationError("\n".join(errors))

    def update(self, data: dict):
        """Update the context with the provided data.

        Args:
            data: The dictionary of items to be merged into the Context. The
                  dictionary is evaluated recursively and merged in with
                  existing levels. Leave nodes are replaced
        """
        for key, value in data.items():
            if hasattr(self, key) and isinstance(getattr(self, key), _Node):
                getattr(self, key).update(value)
            else:
                setattr(self, key, self._create_node(value))

    def set_context(self, key, value):  # noqa: D102 pylint:disable=missing-function-docstring
        setattr(self, key, self._create_node(value))
        return value

    def get_context(self, key):  # noqa: D102 pylint:disable=missing-function-docstring
        return self[key]

    def keys(self):  # noqa: D102 pylint:disable=missing-function-docstring
        return self._keys

    def __setitem__(self, key, item):  # noqa: D105
        # raise Exception(f"Setting {key} to {item}")
        setattr(self, key, self._create_node(item))
