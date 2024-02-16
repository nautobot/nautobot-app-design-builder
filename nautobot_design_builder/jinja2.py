"""Jinja2 related filters and environment methods."""
import json
from typing import TYPE_CHECKING
import yaml

from django.template import engines

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from jinja2.environment import Context as JinjaContext
from jinja2.nativetypes import NativeEnvironment
from jinja2.utils import missing

from netaddr import AddrFormatError, IPNetwork

if TYPE_CHECKING:
    from nautobot_design_builder.context import ContextNodeMixin


def network_string(network: IPNetwork, attr="") -> str:
    """Jinja2 filter to convert the IPNetwork object to a string.

    If an attribute is supplied, first lookup the attribute on the IPNetwork
    object, then convert the returned value to a string.

    Args:
        network (IPNetwork): Object to convert to string
        attr (str, optional): Optional attribute to retrieve from the IPNetwork prior
            to converting to a string. Defaults to "".

    Example:
    ```jinja
          {{ "1.2.3.4/24" | ip_network | network_string("ip") }}
    ```

    Returns:
        str: Converted object
    """
    if attr:
        return str(getattr(network, attr))

    return str(network)


def ip_network(input_str: str) -> IPNetwork:
    """Jinja2 filter to convert a string to an IPNetwork object.

    Args:
        input_str (str): String correctly formatted as an IP Address

    Returns:
        IPNetwork: object that represents the input string
    """
    return IPNetwork(input_str)


def network_offset(prefix: str, offset: str) -> IPNetwork:
    """Jinja2 filter to compute an IPNetwork based off of a prefix and offset.

    Example:
        >>> from design_builder.jinja2 import network_offset
        >>> network_offset("1.1.0.0/16", "0.0.1.1")
        IPNetwork('1.1.1.1/16')

        >>> from design_builder.jinja2 import network_offset
        >>> network_offset("1.1.0.0/16", "0.0.1.0/24")
        IPNetwork('1.1.1.0/24')

    Args:
        prefix (str): Prefix string in the form x.x.x.x/x
        offset (str): Prefix string in the form x.x.x.x/x

    Returns:
        IPNetwork: Returns an IPNetwork that is the result of prefix + offset. The
        returned network object's prefix will be set to the longer prefix length
        between the two inputs.
    """
    try:
        prefix = IPNetwork(prefix)
    except AddrFormatError:
        # pylint: disable=raise-missing-from
        raise AddrFormatError(f"Invalid prefix {prefix}")

    try:
        offset = IPNetwork(offset)
    except AddrFormatError:
        # pylint: disable=raise-missing-from
        raise AddrFormatError(f"Invalid offset {offset}")

    # netaddr overloads the + operator to sum
    # each octet of a pair of addresses. For instance,
    # 1.1.1.1 + 1.2.3.4 = 2.3.4.5
    # The result of the expression is a netaddr.IPAddress
    new_prefix = IPNetwork(prefix.ip + offset.ip)
    if prefix.prefixlen > offset.prefixlen:
        new_prefix.prefixlen = prefix.prefixlen
    else:
        new_prefix.prefixlen = offset.prefixlen
    return new_prefix


def _json_default(value):
    try:
        return value.data
    except AttributeError:
        # pylint: disable=raise-missing-from
        raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def to_json(value: "ContextNodeMixin"):
    """Convert a context node to JSON."""
    return json.dumps(value, default=_json_default)


def to_yaml(value: "ContextNodeMixin", *args, **kwargs):
    """Convert a context node to YAML."""
    default_flow_style = kwargs.pop("default_flow_style", False)

    return yaml.dump(json.loads(to_json(value)), allow_unicode=True, default_flow_style=default_flow_style, **kwargs)


def new_template_environment(root_context, base_dir=None, native_environment=False) -> NativeEnvironment:
    """Create a new template environment that will resolve identifiers using the supplied root_context.

    If base_dir is supplied, templates will be matched from the base directory provided.

    Args:
        root_context (design_builder.context.Context): Context object to use when resolving missing identifiers in the rendering process
        base_dir (str): Path, or list of paths, to use as search paths for finding templates.
        native_environment (bool): To use native JinjaEnvironment

    Returns:
        NativeEnvironment: Jinja native environment
    """

    class RenderContext(JinjaContext):
        """Custom jinja render context that will resolve values from the provided design builder context."""

        def resolve_or_missing(self, key):
            """Resolve the missing value from the current design builder context.

            Args:
                key (str): Variable name to attempt to resolve.

            Returns:
                The resolved value or jinja2.utils.missing
            """
            value = super().resolve_or_missing(key)
            if value is missing:
                if hasattr(root_context, key) or key in root_context:
                    value = root_context[key]
                elif key == "context":
                    value = root_context
            return value

    def context_class(*args, **kwargs):
        context = RenderContext(*args, **kwargs)
        return context

    loader = None
    if base_dir:
        loader = FileSystemLoader(base_dir)

    env_class = Environment
    if native_environment:
        env_class = NativeEnvironment

    env = env_class(
        loader=loader,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    for name, func in engines["jinja"].env.filters.items():
        # Register standard Nautobot filters in the environment
        env.filters[name] = func

    env.filters["to_yaml"] = to_yaml
    env.filters["ip_network"] = ip_network
    env.filters["network_string"] = network_string
    env.filters["network_offset"] = network_offset
    env.context_class = context_class
    return env
