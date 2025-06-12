"""Jinja2 related filters and environment methods."""

from django.template import engines
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from jinja2.environment import Context as JinjaContext
from jinja2.nativetypes import NativeEnvironment
from jinja2.utils import missing


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

    env.context_class = context_class
    return env
