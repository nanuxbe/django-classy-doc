"""ClassyDoc handler for mkdocstrings.

This handler uses django_classy_doc's extraction logic to collect class
documentation and renders it using Jinja templates with collapsible source code.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, ClassVar, Mapping

from mkdocstrings import BaseHandler, CollectionError


class ClassyDocHandler(BaseHandler):
    """Handler for Django class documentation using django_classy_doc.

    This handler allows mkdocstrings to render documentation for Django classes
    with features like collapsible source code, method resolution order display,
    and proper docstring parsing.
    """

    name: ClassVar[str] = "classydoc"
    domain: ClassVar[str] = "py"
    fallback_theme: ClassVar[str] = "material"
    enable_inventory: ClassVar[bool] = False

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the handler.

        This ensures Django is configured before the handler is used.
        """
        super().__init__(**kwargs)
        self._ensure_django_configured()

        # Add custom filters
        self.env.filters["basename"] = lambda path: os.path.basename(path) if path else ""
        self.env.filters["parse_docstring"] = self._parse_docstring
        self.env.filters["format_value"] = self._format_value

    def _parse_docstring(self, docstring: str) -> dict:
        """Parse a Google-style docstring into structured sections."""
        from django_classy_doc.formatters.markdown import GoogleDocstringParser
        return GoogleDocstringParser(docstring).parse()

    def _format_value(self, value: Any, max_length: int = 60) -> str:
        """Format an attribute value for display."""
        import html
        import re

        if value is None:
            return "None"

        value_str = str(value)

        # Decode HTML entities
        value_str = html.unescape(value_str)

        # Clean up class representations: <class 'foo.Bar'> → foo.Bar
        class_match = re.match(r"^<class '([^']+)'>$", value_str)
        if class_match:
            value_str = class_match.group(1)

        # Clean up function repr: <function name at 0x...> → name()
        value_str = re.sub(r'<function ([^\s>]+)[^>]*>', r'\1()', value_str)

        # Clean up bound method repr
        value_str = re.sub(r'<bound method ([^>]+)>', r'\1()', value_str)

        # Truncate long values
        if len(value_str) > max_length:
            value_str = value_str[:max_length - 3] + '...'

        return value_str

    def _ensure_django_configured(self) -> None:
        """Ensure Django is configured for use by the handler.

        If DJANGO_SETTINGS_MODULE is set, use those settings.
        Otherwise, try to configure Django with minimal settings.
        """
        import sys
        import django
        from django.conf import settings

        if settings.configured:
            return

        # Add current working directory to path for settings module discovery
        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.insert(0, cwd)

        # Check if we should use existing settings
        if os.environ.get("DJANGO_SETTINGS_MODULE"):
            django.setup()
            return

        # Minimal Django configuration - user must set DJANGO_SETTINGS_MODULE
        # for proper CLASSY_DOC settings
        settings.configure(
            DEBUG=True,
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
                "django_classy_doc",
            ],
            DATABASES={},
            USE_TZ=True,
        )
        django.setup()

    def get_templates_dir(self, handler: str | None = None) -> Path:
        """Return the path to the handler's templates directory.

        Args:
            handler: The name of the handler (unused, always returns classydoc templates).

        Returns:
            The path to the templates directory.
        """
        return Path(__file__).parent / "templates"

    def collect(self, identifier: str, options: Mapping[str, Any]) -> dict[str, Any]:
        """Collect documentation for a class identifier.

        Args:
            identifier: The fully qualified class name (e.g., 'djadmin.layout.Fieldset').
            options: Configuration options for collection.

        Returns:
            A dictionary containing the class documentation data.

        Raises:
            CollectionError: If the class cannot be found or documented.
        """
        from django_classy_doc.utils import build

        try:
            # Use build() directly instead of build_context() to bypass settings checks
            structure = build(identifier)
        except ImportError as e:
            raise CollectionError(f"Could not import: {identifier}") from e
        except Exception as e:
            raise CollectionError(f"Could not document: {identifier}: {e}") from e

        if structure is False:
            raise CollectionError(f"Could not document: {identifier}")

        # Post-process attributes like build_context does
        from collections import OrderedDict
        for name, lst in structure['attributes'].items():
            for i, definition in enumerate(lst):
                a = definition['defining_class']
                structure['attributes'][name][i]['defining_class'] = (a.__module__, a.__name__)

                if isinstance(definition['object'], list):
                    try:
                        s = '[{0}]'.format(', '.join([c.__name__ for c in definition['object']]))
                    except AttributeError:
                        pass
                    else:
                        structure['attributes'][name][i]['default'] = s

        sorted_attributes = sorted(structure['attributes'].items(), key=lambda t: t[0])
        structure['attributes'] = OrderedDict(sorted_attributes)

        sorted_methods = sorted(structure['methods'].items(), key=lambda t: t[0])
        structure['methods'] = OrderedDict(sorted_methods)

        # Add options to the structure for use in templates
        structure["_options"] = dict(options)

        return structure

    def render(
        self,
        data: dict[str, Any],
        options: Mapping[str, Any],
        *,
        locale: str | None = None,
    ) -> str:
        """Render the collected data using Jinja templates.

        Args:
            data: The collected class documentation data.
            options: Configuration options for rendering.
            locale: Locale for translations (not used).

        Returns:
            Rendered HTML string.
        """
        # Merge default options with provided options
        merged_options = {
            "show_source": True,
            "show_mro": True,
            "show_attributes": True,
            "show_methods": True,
            "show_fields": True,
            "heading_level": 2,
        }
        merged_options.update(options)

        template = self.env.get_template("class.html.jinja")
        return template.render(
            class_data=data,
            config=merged_options,
            heading_level=merged_options["heading_level"],
        )


def get_handler(
    *,
    theme: str,
    custom_templates: str | None = None,
    mdx: list | None = None,
    mdx_config: dict | None = None,
    handler_config: dict | None = None,
    tool_config: Any = None,
    **kwargs: Any,
) -> ClassyDocHandler:
    """Create and return a ClassyDocHandler instance.

    This function is the entry point for mkdocstrings to obtain a handler instance.

    Args:
        theme: The MkDocs theme name.
        custom_templates: Path to custom templates directory.
        mdx: Markdown extensions configuration.
        mdx_config: Markdown extensions configuration options.
        handler_config: Handler-specific configuration.
        tool_config: MkDocs tool configuration.
        **kwargs: Additional keyword arguments.

    Returns:
        A configured ClassyDocHandler instance.
    """
    return ClassyDocHandler(
        theme=theme,
        custom_templates=custom_templates,
        mdx=mdx or [],
        mdx_config=mdx_config or {},
    )
