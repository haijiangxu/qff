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
    "sphinx_rtd_theme",
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'sphinx.ext.todo',
    'sphinx_autodoc_typehints',
]

myst_heading_anchors = 3
myst_enable_extensions = ["deflist", "tasklist", "colon_fence", "dollarmath", "amsmath"]
myst_number_code_blocks = ["python"]

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


html_use_index = True

html_show_sphinx = False
html_show_copyright = True

# Output file base name for HTML help builder.
htmlhelp_basename = 'qffdoc'
# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# -- Options for LaTeX output ---------------------------------------------

# 设置LaTeX编译引擎为xelatex
latex_engine = 'xelatex'

# 设置中文字体，需要安装对应的字体文件
latex_elements = {
    'fontpkg': r'''
                \usepackage{fontspec}
                \usepackage{xeCJK}
                \setmainfont{DejaVu Serif} 
                \setCJKmainfont{SimSun}  
                ''',
    'papersize': 'a4paper',
    'pointsize': '12pt',
    'fncychap': r'\usepackage[Bjornstrup]{fncychap}',
    'preamble': r'''
                    \usepackage{hyperref}
                    \usepackage{geometry}
                    \usepackage{graphicx}
                    \usepackage{ctex}
                    \usepackage{adjustbox}
                    \usepackage{grffile}
                    \usepackage{hyperref}   
                    \usepackage{amsmath} 
                    \usepackage{titling}
                    \geometry{a4paper,left=2cm,right=2cm,top=2cm,bottom=2cm}
                    \graphicspath{{../../_static/}}
                    \usepackage{tocloft}
                    \addtolength{\cftsecnumwidth}{2em}
                    \addtolength{\cftsubsecnumwidth}{2em} 
                    \def\captionsenglish{\def\contentsname{目\quad 录}} % ***
                ''',
    'tableofcontents': r'''
                    \begingroup
                    \pagenumbering{roman}
                    \centering
                    \setcounter{tocdepth}{2}
                    \tableofcontents
                    \newpage
                    \pagenumbering{arabic}
                    \setcounter{page}{1}
                    \endgroup
                ''',
    'makeindex': '\\makeindex',
    'printindex': '\\printindex',
    'sphinxsetup': r'''
                    verbatimwithframe=false,
                    VerbatimColor={rgb}{0.95,0.95,0.95},
                    VerbatimHighlightColor={rgb}{1,1,1},
                    VerbatimBorderColor={rgb}{0.95,0.95,0.95},
                ''',
    'maketitle': r'''
                \begin{titlepage}
                \centering
                \vspace*{3cm}
                {\Huge \textbf{QFF使用手册}} \\
                \vspace{1cm}
                {\Large 版本: %s} \\
                \vspace{2cm}
                \includegraphics[width=1\textwidth]{qff_cover.png} \\
                \vspace{2cm}
                {\Large 作者: 徐海江} \\
                 \vspace{1cm}
                {\large \today} \\
        \end{titlepage}
    ''' % version,
}


