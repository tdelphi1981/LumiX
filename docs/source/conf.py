# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "LumiX"
copyright = "2024, LumiX Contributors"
# For specific author information, see the AUTHORS file in the project root
author = "LumiX Contributors"
release = "0.1.0"
version = "0.1.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinxcontrib.mermaid",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
html_title = "LumiX Documentation"
html_logo = "_static/Lumix_Logo_1024.png"

html_theme_options = {
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
    "top_of_page_button": "edit",
}

# -- Extension configuration -------------------------------------------------

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}
autodoc_typehints = "description"
autodoc_type_aliases = {}

# Autosummary settings
autosummary_generate = True
autosummary_imported_members = False

# Suppress duplicate object warnings and forward reference warnings
suppress_warnings = [
    "app.add_node",
    "app.add_directive",
    "app.add_role",
    "autodoc",
    "ref.python",
]

# Autodoc configuration - suppress member warnings
autodoc_warningiserror = False

# Configuration to handle duplicate warnings from autosummary
# These warnings occur when objects are documented both in main docs and API reference
# This is expected behavior when using autosummary to generate API documentation
import logging
import re


class DuplicateFilter(logging.Filter):
    """Filter to suppress duplicate object description warnings."""

    def filter(self, record):
        # Suppress duplicate object warnings
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            if 'duplicate object description' in record.msg:
                return False
        return True


# Apply the filter to sphinx loggers
def setup(app):
    """Configure logging to suppress duplicate warnings."""
    # Add filter to all sphinx loggers
    for logger_name in ['sphinx', 'sphinx.ext.autodoc', 'sphinx.ext.autosummary']:
        logger = logging.getLogger(logger_name)
        logger.addFilter(DuplicateFilter())

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

# Mermaid configuration
mermaid_version = "latest"
mermaid_init_js = """
mermaid.initialize({
    startOnLoad: true,
    theme: 'neutral',
    flowchart: {
        useMaxWidth: true,
        htmlLabels: true
    }
});
"""

# Todo extension
todo_include_todos = True

# RST substitutions
rst_prolog = """
.. |x| replace:: x
.. |var| replace:: var
"""
