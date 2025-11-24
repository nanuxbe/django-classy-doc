"""ClassyDoc handler for mkdocstrings.

This handler allows mkdocstrings to render documentation for Django classes
using django_classy_doc's extraction and formatting capabilities.
"""

from mkdocstrings_handlers.classydoc.handler import ClassyDocHandler, get_handler

__all__ = ["ClassyDocHandler", "get_handler"]
