"""Jinja2 related filters and environment methods."""
import re
import yaml

from jinja2 import Environment, FileSystemLoader, StrictUndefined, nodes
from jinja2.environment import Context as JinjaContext
from jinja2.ext import Extension
from jinja2.lexer import TOKEN_DATA, TokenStream
from jinja2.nativetypes import NativeEnvironment
from jinja2.utils import missing

from netaddr import AddrFormatError, IPNetwork
from netutils.utils import jinja2_convenience_function


class TrackingTokenStream:
    """Track leading whitespace in the token stream."""

    def __init__(self, parent: TokenStream):
        """Initialize the tracking token stream.

        Args:
            parent (jinja2.TokenStream): The token stream to watch.
        """
        self._parent = parent
        self.prefix = ""

    def __iter__(self):
        """Makes class iterable, returns instance of self."""
        return self

    def __next__(self):
        """Get the next token from the stream, record any leading whitespace."""
        current = self._parent.current
        if current.type == TOKEN_DATA:
            index = current.value.rfind("\n")
            if index >= 0:
                self.prefix = current.value[index + 1 :]  # noqa: E203
            else:
                self.prefix = current.value
        return self._parent.__next__()


class IndentationExtension(Extension):
    """Add an indent tag to Jinja2 that will indent a block with any whitespace preceding the tag.

    This adds the ability to prepend each line of a block with leading whitespace characters. This is
    especially useful when rendering content such as YAML, which depends on correct indentation. A
    typical usage is:

    ```jinja
          {%+ indent %}{% include "path/to/template.j2" %}{% endindent %}
    ```

    Note the leading `+` just after the block start. This is necessary if lstrip_blocks is enabled
    in the environment. `lstrip_blocks=True` prevents the indent tag from ever getting the leading
    whitespace. However, the `+` will preserve leading whitespace despite lstrip_blocks.
    """

    stream: None
    tags = {"indent"}

    def filter_stream(self, stream):
        """Set up stream filtering to watch for leading white space.

        Args:
            stream (jinja2.TokenStream): The input token stream to watch

        Returns:
            TrackingTokenStream: The returned token stream is a passthrough to the
            input token stream, it only records whitespace occurring before tokens.
        """
        self.stream = TrackingTokenStream(stream)
        return self.stream

    def parse(self, parser):
        """Parse the indent block.

        Args:
            parser (_type_): The active jinja2 parser

        Returns:
            jinja2.nodes.CallBlock: A CallBlock is returned that, when called, will
            process the wrapped block and prepend indentation on each line.
        """
        token = next(parser.stream)
        lineno = token.lineno
        whitespace = re.sub(r"[^\s]", " ", self.stream.prefix)

        body = parser.parse_statements(["name:endindent"], drop_needle=True)
        args = [nodes.TemplateData(whitespace)]
        return nodes.CallBlock(self.call_method("_indent_support", args), [], [], body).set_lineno(lineno)

    def _indent_support(self, indentation, caller):  # pylint: disable=no-self-use
        """Perform the block indentation.

        Args:
            indentation (str): Whitespace to be prepended to each line
            caller (_type_): Wrapped jinja2 block

        Returns:
            str: Processed block where each line has been prepended with whitespace.
        """
        body = caller()
        lines = body.split("\n")
        for i in range(1, len(lines)):
            if lines[i]:
                lines[i] = indentation + lines[i]
        return "\n".join(lines)


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
        input (str): String correctly formatted as an IP Address

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
        raise AddrFormatError(f"Invalid prefix {prefix}")

    try:
        offset = IPNetwork(offset)
    except AddrFormatError:
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


def __yaml_context_dumper(*args, **kwargs):
    from .context import Context

    dumper = yaml.Dumper(*args, **kwargs)
    dumper.add_representer(Context, Context.representer)
    for klass, representer in Context.representers.items():
        dumper.add_representer(klass, representer)
    return dumper


def to_yaml(obj, *args, **kwargs):
    """Convert an object to YAML."""
    default_flow_style = kwargs.pop("default_flow_style", False)
    return yaml.dump(
        obj, allow_unicode=True, default_flow_style=default_flow_style, Dumper=__yaml_context_dumper, **kwargs
    )


def new_template_environment(root_context, base_dir=None, native_environment=False):
    """Create a new template environment that will resolve identifiers using the supplied root_context.

    If base_dir is supplied, templates will be matched from the base directory provided.

    Args:
        root_context (design_builder.context.Context): Context object
        to use when resolving missing identifiers in the rendering process
        base_dir (str): Base directory to search from for templates

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
        extensions=[IndentationExtension],
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    for name, func in jinja2_convenience_function().items():
        # Register in django_jinja
        env.filters[name] = func

    env.filters["to_yaml"] = to_yaml
    env.filters["ip_network"] = ip_network
    env.filters["network_string"] = network_string
    env.filters["network_offset"] = network_offset
    env.context_class = context_class
    return env
