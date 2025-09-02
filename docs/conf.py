# Copyright 2023-2025 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import os
import pathlib
import sys

project = "Starflow"
author = "Canonical Group Ltd"
# The version to append to the project title. Since Starflow doesn't have versions, keep
# blank by default. Append "dev" for PR builds.
if (
    "READTHEDOCS_VERSION_TYPE" in os.environ
    and os.environ["READTHEDOCS_VERSION_TYPE"] == "external"
):
    release = "dev"

copyright = "2015-%s, %s" % (datetime.date.today().year, author)

# region Configuration for canonical-sphinx
ogp_site_url = "https://canonical-starflow.readthedocs-hosted.com"
ogp_site_name = project

# Project slug; see https://meta.discourse.org/t/what-is-category-slug/87897
#
# TODO: If your documentation is hosted on https://docs.ubuntu.com/,
#       uncomment and update as needed.

# slug = "starflow"

html_context = {
    "product_page": "github.com/canonical/starflow",
    "github_url": "https://github.com/canonical/starflow",
    "repo_default_branch": "main",
    "repo_folder": "/docs/",
    "github_issues": "enabled",
    "discourse": "https://discourse.canonical.com",
    "display_contributors": False,
}

# Target repository for the edit button on pages
html_theme_options = {
    "source_edit_link": "https://github.com/canonical/starflow",
}

extensions = [
    "canonical_sphinx",
    "sphinx_sitemap",
    "pydantic_kitbash",
    "sphinx.ext.ifconfig",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.details.directive",
    "sphinx_toolbox.collapse",
    "sphinxext.rediraffe",
]

sphinx_tabs_disable_tab_closing = True
# endregion

#rst_epilog = """
#.. include:: /reuse/links.txt
#"""

exclude_patterns = [
    "sphinx-docs-starter-pack",
    "how-to",
    "reference",
]

# region Options for extensions

# Client-side page redirects.
rediraffe_redirects = "redirects.txt"

# Sitemap configuration: https://sphinx-sitemap.readthedocs.io/
html_baseurl = "https://canonical-starflow.readthedocs-hosted.com"

if "READTHEDOCS_VERSION" in os.environ:
    version = os.environ["READTHEDOCS_VERSION"]
    sitemap_url_scheme = "{version}{link}"
else:
    sitemap_url_scheme = "latest/{link}"

# endregion
