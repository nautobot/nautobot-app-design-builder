"""Module that contains classes and functions for use with Design Builder context available when using Jinja templating."""
from functools import cached_property
from collections import UserList, UserDict, UserString
import inspect
from typing import Any
import yaml

from jinja2.nativetypes import NativeEnvironment

from nautobot.extras.models import JobResult

from nautobot_design_builder.errors import DesignValidationError
from nautobot_design_builder.jinja2 import new_template_environment
from nautobot_design_builder.logging import LoggingMixin
from nautobot_design_builder.util import load_design_yaml


class ContextNodeMixin:
    """A mixin to help create tree nodes for the Design Builder context.

    This mixin provides overridden __getitem__ and __setitem__ magic
    methods that will automatically get and set the tree node types. The
    mixin also provides a mechanism for a node within the tree to find
    the context's root node and root render environment.
    """

    _parent: "ContextNodeMixin" = None
    _env: NativeEnvironment = None

    @cached_property
    def root(self) -> "ContextNodeMixin":
        """Lookup and return the root node in the context tree.

        Returns:
            ContextNodeMixin: root node
        """
        node: ContextNodeMixin = self
        while node._parent is not None:  # pylint:disable=protected-access
            node = node._parent  # pylint:disable=protected-access

        if node._env is None:  # pylint:disable=protected-access
            node._env = new_template_environment(node, native_environment=True)  # pylint:disable=protected-access
        return node

    @property
    def env(self) -> NativeEnvironment:
        """Lookup the Jinja2 native environment from the root context node."""
        return self.root._env  # pylint:disable=protected-access

    def __repr__(self) -> str:
        """Get the printable representation of the node.

        This will return the `repr` of either the node's container `data`
        attribute (if it exists) or the super class representation.
        """
        if hasattr(self, "data"):
            return repr(getattr(self, "data"))
        return super().__repr__()

    def __setitem__(self, key: "int | str", value: Any) -> "ContextNodeMixin":
        """Store a new value within the node.

        Args:
            key (int | str): Index/key/attribute name
            value (Any): Value of item to store

        Raises:
            KeyError: if the item cannot be stored.

        Returns:
            ContextNodeMixin: _description_
        """
        if not isinstance(value, ContextNodeMixin):
            value = self._create_node(value)

        if hasattr(self, "data") and key in self.data:
            old_value = self.data[key]
            if hasattr(old_value, "update"):
                old_value.update(value)
            else:
                self.data[key] = value
        elif isinstance(key, str) and hasattr(self, key):
            setattr(self, key, value)
        else:
            super().__setitem__(key, value)
        return value

    def __getitem__(self, key) -> "ContextNodeMixin":
        """Get the desired item from within the node's children.

        `__getitem__` will first look for items in the context
        node's `data` attribute. If the `data` attribute does
        not exist, than the lookup will default to the superclass
        `__getitem__`. If the found item is a `_TemplateNode` then
        the template is rendered and the resulting native type is
        returned.
        """
        try:
            value = self.data[key]
        except KeyError as ex:
            if isinstance(key, str) and hasattr(self, key):
                value = getattr(self, key)
            else:
                raise ex
        except AttributeError:
            value = super().__getitem__(key)

        # Use the _TemplateNode's data descriptor to
        # render the template and get the native value
        if isinstance(value, _TemplateNode):
            value = value.data
        return value

    def _create_node(self, value):
        """`_create_node` is a factory function for context nodes.

        `_create_node` will take a value and create the proper tree
        node type. Python types `list`, `dict` and `str` are converted
        to the associated `_ListNode`, `_DictNode`, and `_TemplateNode`
        with all other types being returned unchanged. If a context
        node is created, than it's parent node is properly set so
        that the root node, and environment, of the context can be
        determined for `_TemplateNode` rendering.

        Args:
            value: a value that needs to be added a parent node

        Returns:
            A new Node. If the value is a list then a new _ListNode is returned
            if the value is a dict then a new _DictNode, if the value is a string
            then a new _TemplateNode, otherwise the original value (a leaf node)
            is returned.
        """
        if isinstance(value, list):
            value = _ListNode(value)

        elif isinstance(value, dict):
            value = _DictNode(value)

        elif isinstance(value, str):
            value = _TemplateNode(self, value)

        if isinstance(value, ContextNodeMixin):
            value._parent = self  # pylint:disable=protected-access

        return value


class _Template:
    """`_Template` is a Python descriptor to render Jinja templates.

    `_Template` can be used to assign Jinja templates to object
    attributes. When the attribute is retrieved the template will
    be automatically rendered before it is returned.
    """

    def __get__(self, obj: "_TemplateNode", objtype=None) -> Any:
        """Render the template and return the native type."""
        _template = getattr(obj, "_data_template", None)
        if _template is None:
            data = getattr(obj, "_data")
            _template = obj._parent.env.from_string(data)
            setattr(obj, "_data_template", _template)

        return _template.render()

    def __set__(self, obj, value):
        """Set a new template for future rendering."""
        setattr(obj, "_data", value)
        setattr(obj, "_data_template", None)


class _TemplateNode(UserString):
    """A TemplateNode represents a string or jinja2 template value.

    _TemplateNode inherits from `collections.UserString` and follows the
    conventions in that base class. See the `collections` documentation for
    more information.

    Args:
        parent: The root node to be used when looking up variables in the context tree
        seq: a jinja template to be rendered at a later time. This can also be a literal
        string.
    """

    data = _Template()

    def __init__(self, parent: ContextNodeMixin, seq):
        self._parent = parent
        if isinstance(seq, _TemplateNode):
            seq = seq._data

        super().__init__(seq)

    def update(self, seq):
        """Update the node with a new template or string literal."""
        if isinstance(seq, str):
            self.data = seq
        elif isinstance(seq, UserString):
            self.data = seq.data[:]
        elif isinstance(seq, _TemplateNode):
            self.data = seq._data  # pylint:disable=protected-access
        else:
            self.data = str(seq)


class _ListNode(ContextNodeMixin, UserList):
    """`_ListNode` is a `collections.UserList` that can be used as a context node.

    This type inherits from `collections.UserList` and should behave
    the same way as that type. The only functionality added to
    `collections.UserList` is that upon initialization all items
    in the underlying data structure are converted to the appropriate
    node type for the context tree (`_ListNode`, `_DictNode`, or
    `_TemplateNode`)
    """

    def __init__(self, initlist=None):
        super().__init__(initlist)
        for i, item in enumerate(self.data):
            self.data[i] = self._create_node(item)


class _DictNode(ContextNodeMixin, UserDict):
    """`_DictNode` is a `collections.UserDict` that can be used as a context node.

    The `_DictNode` behaves the same as a typical dict/`collections.UserDict`
    with the exception that all dictionary keys are also available as object
    attributes on the node.
    """

    def __getattr__(self, attr) -> Any:
        """Retrieve the dictionary key that matches `attr`.

        If no dictionary key exists matching the attribute name then
        an `AttributeError` is raised.

        Args:
            attr: Attribute name to lookup in the dictionary

        Raises:
            AttributeError: If no dictionary key matching the attribute
            name exists.

        Returns:
            Any: The value of the item with the matching dictionary key.
        """
        if attr in self.data:
            return self[attr]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{attr}'")


def context_file(*ctx_files):
    """Add a context file to a class.

    Context Files are only loaded once per class hierarchy, even if they are
    specified more than once in a class/subclass tree. Context files must
    be in YAML format. Each context file will be loaded and parsed and
    merged together to form a base context.
    """

    def wrapper(context_cls):
        if "__base_contexts" not in context_cls.__dict__:
            setattr(context_cls, "__base_contexts", set())

        for ctx_file in ctx_files:
            base_context = getattr(context_cls, "__base_contexts")
            base_context.add(ctx_file)

        return context_cls

    return wrapper


class Context(_DictNode, LoggingMixin):
    """A context represents a tree of variables that can include templates for values.

    The Design Builder context is a tree structure that can be used for a
    Jinja2 render context. One of the strengths of using the Design Builder
    context is that context information can be provided both in a
    python class (as normal properties and methods) as well as in YAML
    files that can be loaded.

    YAML files are loaded in and merged with the context, so many files
    can be loaded to provide a complete context. This allows the context
    files to be organized in whatever structure makes sense to the
    design author.

    Another strength of the context is that string values can be Jinja
    templates that will render native Python types. The template render
    context is the context tree root. This means that values within the
    context tree can be used to compute other values at render time.

    Args:
        data: a dictionary of values to be loaded into the context. This dictionary
              will be recursively evaluated and each level will be stored as either
              a _DictNode or _ListNode. Leaves will be stored either as a _TemplateNode
              or their native type.
    """

    def __init__(self, data: dict = None, job_result: JobResult = None):
        """Constructor for Context class that creates data nodes from input data."""
        super().__init__(data)
        self.job_result = job_result

        for base, filename in self.base_context_files():
            context = load_design_yaml(base, filename)
            # don't add anything if the file was empty
            if context:
                self.update(context)

    @classmethod
    def base_context_files(cls):
        """Calculate the complete list of context files for the class."""
        bases = list(inspect.getmro(cls))
        bases.reverse()

        files = []
        for base in bases:
            for filename in base.__dict__.get("__base_contexts", {}):
                files.append((base, filename))
        return files

    @classmethod
    def base_context(cls) -> "Context":
        """The base context is the combination of any context_files that have been added to a context.

        Calling base_context will merge all of the context trees that have been added by the
        @context_file decorator.

        Returns:
            Context: Merged context tree
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
            DesignValidationErrors: raised by the validators will be collected. and a single DesignValidationError will be raised that includes all the error messages.
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
