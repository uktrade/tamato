# -*- coding: utf-8 -*-
# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath("../.."))


# -- Project information -----------------------------------------------------

project = "Tariff Management Tool"
copyright = "2021, Department for International Trade"
author = "Department for International Trade"

# The full version, including alpha/beta/rc tags
release = "1.0.0"


# -- General configuration ---------------------------------------------------

import django

os.environ["DJANGO_SETTINGS_MODULE"] = "settings.test"
django.setup()

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "govuk_tech_docs_sphinx_theme",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.graphviz",
]

# Output in accessible SVG by default
graphviz_output_format = "svg"
graphviz_dot_args = [
    "-Gfontname=Arial",
    "-Nfontname=Arial",
    "-Efontname=Arial",
    "-Nstyle=filled",
    "-Nfillcolor=white",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "node_modules", "venv"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "govuk_tech_docs_sphinx_theme"

html_context = {
    "github_url": "https://github.com/uktrade/tamato",  # if using GitHub, set to the URL of your repository as a string
    "gitlab_url": None,  # if using GitLab, set to the URL of your repository as a string
    "conf_py_path": "docs/",  # assuming your Sphinx folder is called `docs`
    "version": "main",  # assuming `main` is your repository's default branch
    "accessibility": "accessibility.md",  # assuming your accessibility statement is at `docs/accessibility.md`
}
# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    "organisation": "DIT",  # replace with your organisation's abbreviation (ideally) or name - long text may not look nice
    "phase": "Alpha",  # replace with an Agile project phase - see https://www.gov.uk/service-manual/agile-delivery
}
# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
