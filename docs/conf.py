# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import sys
import os
import re
import ast
from datetime import datetime


sys.path.insert(0, os.path.abspath('../'))


def get_version_string() -> str:
    """
    Get the  version number
    :return: version number
    :rtype: str, e.g. '0.6.24'

    """
    with open("../qff/__init__.py", "rb") as _f:
        version_line = re.search(
            r"__version__\s+=\s+(.*)", _f.read().decode("utf-8")
        ).group(1)
        return str(ast.literal_eval(version_line))


# latex_engine = "xelatex"
# latex_use_xindy = False
# latex_elements = {
#     "preamble": "\\usepackage[UTF8]{ctex}\n",
# }

source_suffix = [".rst", ".md"]

# -- Project information -----------------------------------------------------

project = 'QFF'
copyright = f"2019–{datetime.now().year}"
author = 'xuhaijiang'
version = get_version_string()

# -- General configuration ---------------------------------------------------

# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    "myst_parser",
    "sphinx_rtd_theme"
]

templates_path = ['_templates']
html_static_path = ['_static']
# exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
# exclude_patterns = ["_build", "**.ipynb_checkpoints"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"
# html_theme = 'alabaster'
html_logo = './_static/logo.svg'
master_doc = "index"

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.

html_show_sphinx = False
