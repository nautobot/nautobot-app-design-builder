"""Useful jinja2 filters for designs."""

import json
from typing import Any

import yaml
from django_jinja import library
from netaddr import AddrFormatError, IPNetwork


@library.filter
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


@library.filter
def ip_network(input_str: str) -> IPNetwork:
    """Jinja2 filter to convert a string to an IPNetwork object.

    Args:
        input_str (str): String correctly formatted as an IP Address

    Returns:
        IPNetwork: object that represents the input string
    """
    return IPNetwork(input_str)


@library.filter
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


def _json_default(value: Any):
    try:
        return value.data
    except AttributeError:
        # pylint: disable=raise-missing-from
        raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


@library.filter
def to_json(value: Any) -> str:
    """Jinja2 filter to render a value to properly formatted JSON.

    This method will render a value to proper JSON. If the value is part of a Design
    Builder render context, then the correct type encoding (dictionary, list, etc) is
    used. The Nautobot `render_json` method does not handle `UserDict` or `UserList`
    which are the primary collection types for Design Builder contexts. This implementation
    will unwrap those types and render the contained data.

    Args:
        value (Any): The value to be encoded as JSON.

    Returns:
        str: JSON encoded value.
    """
    return json.dumps(value, default=_json_default)


@library.filter
def to_yaml(value: Any, **kwargs) -> str:
    """Jinja2 filter to render a value to properly formatted YAML.

    This method will render a value to proper YAML. If the value is part of a Design
    Builder render context, then the correct type encoding (dictionary, list, etc) is
    used. The Nautobot `render_yaml` method does not handle `UserDict` or `UserList`
    which are the primary collection types for Design Builder contexts. This implementation
    will unwrap those types and render the contained data.

    Args:
        value (Any): The value to be rendered as YAML.
        kwargs (Any): Any additional options to pass to the yaml.dump method.

    Returns:
        str: YAML encoded value.
    """
    default_flow_style = kwargs.pop("default_flow_style", False)

    return yaml.dump(json.loads(to_json(value)), allow_unicode=True, default_flow_style=default_flow_style, **kwargs)
