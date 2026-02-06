#!/usr/bin/env python3
from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    raise SystemExit(
        "Error: this script requires Python 3.12 or higher for tomllib. "
        "Use a higher version of python with uv:\n"
        'uv run --python ">=3.12" ./contributors.py'
    )

import argparse
import base64
import functools
import html
import json
import logging
import os
import pathlib
import re
import textwrap
import tomllib
from dataclasses import dataclass, field
from typing import Any, Sequence
from urllib.request import urlopen, Request

"""
Generates a list of Github contributors to a *craft project and its craft libraries
between two refs.

See usage and examples with:

  ./contributors.py --help
"""

logger = logging.getLogger(__name__)

OWNER = "canonical"
"""Github owner/org for the project and libraries."""

LIBRARY_PATTERN = re.compile("^craft-.*")
"""A regex string of libraries to inspect."""

PR_PATTERN = re.compile(r".+?\s+\(#(\d+)\)$")
"""A regex string to the PR number from a github header.

For example, this extracts '1234' from 'feat: do something (#1234)'.
"""

GITHUB_API = f"https://api.github.com/repos/{OWNER}"
"""URL for Github API requests."""

AUTHOR_FILTER = {
    "Copilot",
    "dependabot[bot]",
    "renovate[bot]",
}
"""Authors to ignore."""


# this mapping could be made programatically (note that craft-grammar has a different URL)
RELEASE_NOTES = {
    "charmcraft": "https://documentation.ubuntu.com/charmcraft/stable/release-notes/",
    "imagecraft": "https://documentation.ubuntu.com/imagecraft/latest/release-notes/",
    "rockcraft": "https://documentation.ubuntu.com/rockcraft/stable/release-notes/",
    "snapcraft": "https://documentation.ubuntu.com/snapcraft/stable/release-notes/",
    "craft-application": "https://canonical-craft-application.readthedocs-hosted.com/latest/reference/changelog/",
    "craft-archives": "https://canonical-craft-archives.readthedocs-hosted.com/en/latest/changelog/",
    "craft-cli": "https://canonical-craft-cli.readthedocs-hosted.com/en/latest/changelog/",
    "craft-grammar": "https://craft-grammar.readthedocs.io/en/latest/changelog/",
    "craft-parts": "https://canonical-craft-parts.readthedocs-hosted.com/latest/reference/changelog/",
    "craft-platforms": "https://canonical-craft-platforms.readthedocs-hosted.com/en/latest/reference/changelog/",
    "craft-providers": "https://canonical-craft-providers.readthedocs-hosted.com/en/latest/reference/changelog/",
    "craft-store": "https://canonical-craft-store.readthedocs-hosted.com/en/latest/reference/changelog/",
}
"""Links to release note pages."""


@dataclass
class Commit:
    """Information about a commit."""

    hash: str
    """Commit hash."""

    header: str
    """Header or title of the commit."""

    author: str
    """The author of the commit."""

    def __str__(self) -> str:
        return f"{self.author} {self.hash} {self.header}"


@dataclass
class Repo:
    """Information about a repository.

    This can represent the project or a library.
    """

    old: str | None = None
    """Old version."""

    new: str | None = None
    """New (updated) version."""

    commits: list[Commit] = field(default_factory=list)
    """Commits between the two versions."""


# region CLI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contributors",
        description=textwrap.dedent(
            """
            Summary:
              Generates a list of Github contributors to a *craft project and its craft libraries between two refs.

            Example:
              contributors --project snapcraft --old-ref 8.13.2 --new-ref 8.14.0
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show debug information and be more verbose",
    )
    parser.add_argument(
        "--project",
        required=True,
        help="The name of the project to inspect.",
    )
    parser.add_argument(
        "--old-ref",
        required=True,
        dest="old_ref",
        help="The older refspec. This can be a tag or hash.",
    )
    parser.add_argument(
        "--new-ref",
        required=True,
        dest="new_ref",
        help="The newer refspec. This can be a tag or hash.",
    )

    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line args."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args


def set_verbosity(verbose: bool) -> None:
    """Set the logging level to info or debug."""
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False


# endregion
# region Github API


# caching means we only log the warning once
@functools.lru_cache(maxsize=1)
def get_token() -> str | None:
    """Get the github token from the environment."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        logger.info("Couldn't find GITHUB_TOKEN in the environment.")
        logger.info("You'll be rate-limited and restricted to public repos.")
        logger.info(
            "To generate a token, go to https://github.com/settings/personal-access-tokens"
        )
        logger.info("For public projects, the token doesn't need any permissions.")
    return token


@functools.lru_cache(maxsize=1)
def get_headers() -> dict[str, str]:
    """Get headers for a Github API request."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
    }
    if token := get_token():
        headers["Authorization"] = f"Bearer {token}"
    return headers


def query_github(url: str) -> dict[str, Any]:
    """Query a github URL and return the data."""
    req = Request(url, headers=get_headers())
    logger.debug(f"Querying {url}")
    with urlopen(req) as r:
        return json.load(r)


def get_uv_lock_file(project: str, ref: str) -> list[dict[str, Any]]:
    """Get a uv lockfile from a github project and the list of packages."""
    url = f"{GITHUB_API}/{project}/contents/uv.lock?ref={ref}"
    data = query_github(url)
    content = base64.b64decode(data["content"]).decode("utf-8")
    data = tomllib.loads(content)
    return data.get("package", [])


def count_commits(name: str, data: dict[str, Any]) -> None:
    """Warn if there are more commits than can be shown.

    If you run into this, the fix would be reworking the single API call
    into a set of API calls that collects commits in batches.
    """
    total = data.get("total_commits", 0)
    returned = len(data.get("commits", []))
    if total > returned:
        logger.warning(
            f"There are more commits for {name} than can be retrieved, contributor list may be incomplete.\n"
            f"total: {total}, returned: {returned}"
        )


def get_commits(name: str, old: str, new: str) -> list[Commit]:
    """Returns a list of git commits."""
    url = f"{GITHUB_API}/{name}/compare/{old}...{new}"
    logger.info(f"Getting {name} commits")
    data = query_github(url)
    count_commits(name, data)

    commits: list[Commit] = []
    for commit in data["commits"]:
        sha = commit["sha"][:7]
        message = commit["commit"]["message"].splitlines()[0]
        if commit.get("author") and commit["author"].get("login"):
            author = commit["author"]["login"]
        else:
            author = "unknown"
        if author in AUTHOR_FILTER:
            continue
        commits.append(Commit(sha, message, author))
    return commits


# endregion
# region logging


def log_versions(repos: dict[str, Repo]) -> None:
    """Log repo versions in a simple table."""
    logger.info(f"     {'project':<20}  {'old':<9}     {'new':<9}")
    logger.info(f"{'-' * 19}     {'-' * 9}     {'-' * 9}")

    for name, data in repos.items():
        old = data.old or "n/a"
        new = data.new or "n/a"
        logger.info(f"{name:<20}     {old:<9}     {new:<9}")


def log_commits(repos: dict[str, Repo]) -> None:
    """Log commits made in all repos."""
    for name, repo in repos.items():
        if repo.commits:
            logger.info(f"\n{name} ({repo.old} -> {repo.new}):")
            for commit in repo.commits:
                logger.info(f"  {commit}")
        else:
            logger.info(f"\n{name} ({repo.old}):")
            logger.info("  no changes")


def log_contributors(repos: dict[str, Repo]) -> None:
    """Log a list of unique authors, formatted for an rst release note page."""
    logger.info("\nContributor list:")
    contributors = get_contributors(repos)
    for i, contributor in enumerate(contributors):
        is_last = i == len(contributors) - 1
        if is_last:
            logger.info(f"and {contributor}")
        else:
            logger.info(f"{contributor},")


# endregion
# region html page

HTML_TEMPLATE = textwrap.dedent(
    """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>Commits, Changes, and Contributors</title>
    <style>
    body {
        font-family: monospace;
        line-height: 1.4;
        background-color: #4a4949;
        color: #f0f0f0;
    }

    h2 {
        margin-top: 1em;
        color: #f0f0f0;
    }

    .commit {
        margin-left: 4em;
    }

    /* Links */
    a {
        color: #87ceeb;  /* default link color - light blue */
        text-decoration: none;
    }

    a:hover {
        text-decoration: underline;
    }

    /* visited links */
    a:visited {
        color: #b0e0ff;  /* brighter / lighter blue for visited links */
    }


    /* strike through commit when checkbox is checked */
    .commit input[type="checkbox"]:checked + span {
        text-decoration: line-through;
        color: #888; /* dim checked commits */
    }

    /* table styling */
    table {
        border-collapse: collapse;
        table-layout: auto;
        border: 1px solid #555;
        margin-top: 1em;
        background-color: #2b2b2b;
    }

    th, td {
        border: 1px solid #555;
        padding: 4px 8px;
        text-align: left;
        font-family: monospace;
    }

    th {
        background-color: #3c3c3c;
        color: #f0f0f0;
    }

    th.sortable { cursor: pointer; }
    th.sortable:after { content: " ↕"; color: #888; }

    thead {
        background-color: #3c3c3c;
    }

    td {
        color: #f0f0f0;
    }

    /* hover highlight for rows */
    tr:hover {
        background-color: #3a3a3a;
    }

    /* strikethrough on check */
    tr.done td {
      text-decoration: line-through;
      color: #888;
    }
    tr.done a { color: #888; }
    </style>
    <script>
    function sortTable(th, col, type) {
      const table = th.closest('table');
      const tbody = table.tBodies[0];
      const rows = Array.from(tbody.rows);

      // toggle direction per column
      const dir = (th.dataset.dir = (th.dataset.dir === 'asc' ? 'desc' : 'asc')) === 'asc' ? 1 : -1;

      const getKey = (tr) => {
        const cell = tr.cells[col];
        if (!cell) return '';
        const text = cell.textContent.trim();
        if (type === 'num') return parseFloat(text.replace(/[^0-9.\\-]/g, '')) || 0;
        return text.toLowerCase();
      };

      rows.sort((a,b) => (getKey(a) > getKey(b) ? 1 : getKey(a) < getKey(b) ? -1 : 0) * dir);

      // reattach in new order
      rows.forEach(r => tbody.appendChild(r));
    }
    </script>

    </head>
    <body>
    <h1>Commits, Changes, and Contributors</h1>
    <!-- REPO_ROWS -->
    </body>
    </html>
    """
)


def hyperlink_release_notes(repo_name: str) -> str | None:
    """Add an inline link to the repo's release notes."""
    url = RELEASE_NOTES.get(repo_name)

    if url:
        return f"<a href='{html.escape(url)}' target='_blank'>release notes</a>"

    return None


def hyperlink_project(repo_name: str) -> str:
    """Return a hyperlink to a project."""
    url = f"https://github.com/{OWNER}/{repo_name}"
    escaped = html.escape(repo_name)
    return f"<a href='{html.escape(url)}' target='_blank'>{escaped}</a>"


def hyperlink_commit(repo_name: str, commit: Commit) -> str:
    """Add an inline link to the PR."""
    match = PR_PATTERN.match(commit.header)
    if match:
        pr_number = match.group(1)
        pr_link = f"https://github.com/canonical/{repo_name}/pull/{pr_number}"
        return f"<a href='{html.escape(pr_link)}' target='_blank'>#{html.escape(pr_number)}</a>"
    return html.escape("n/a")


def generate_versions_table(repos: dict[str, Repo]) -> str:
    """Generate a table of version changes."""
    rows = []

    header = textwrap.dedent(
        """<thead>
             <tr>
               <th>project</th>
               <th>old</th>
               <th>new</th>
             </tr>
           </thead>
           """
    )
    rows.append(header)

    body_rows = []
    for name, data in repos.items():
        row_html = (
            "<tr>"
            f"<td>{html.escape(name)}</td>"
            f"<td>{html.escape(data.old or 'n/a')}</td>"
            f"<td>{html.escape(data.new or 'n/a')}</td>"
            "</tr>"
        )
        body_rows.append(row_html)

    body = "<tbody>\n" + "\n".join(body_rows) + "\n</tbody>"
    rows.append(body)

    return f"<table>{'\n'.join(rows)}</table>"


def generate_contributors_html(repos: dict[str, Repo]) -> str | None:
    """Generate a <pre> block of contributors, to be copied into an rst file."""
    if contributors := get_contributors(repos):
        row = "<h2>Contributors</h2>"
        row += "<pre>\n"
        for i, contributor in enumerate(contributors):
            is_last = i == len(contributors) - 1
            if is_last:
                row += f"and {html.escape(contributor)}"
            else:
                row += f"{html.escape(contributor)},\n"
        row += "</pre>\n"
        return row
    return None


def generate_commit_table(repo_name: str, commits: list[Commit]) -> str:
    """Generate a table of commits."""
    rows = []

    header = textwrap.dedent(
        """<thead>
             <tr>
             <th>check</th>
             <th class="sortable" onclick="sortTable(this, 1, 'text')">header</th>
             <th class="sortable" onclick="sortTable(this, 2, 'text')">PR</th>
             <th class="sortable" onclick="sortTable(this, 3, 'text')">author</th>
             <th class="sortable" onclick="sortTable(this, 4, 'text')">hash</th>
             </tr>
           </thead>
           """
    )
    rows.append(header)

    body_rows = []
    for commit in commits:
        row_html = (
            "<tr>"
            "<td><input type='checkbox' onchange='this.closest(\"tr\").classList.toggle(\"done\", this.checked)'></td>"
            f"<td>{html.escape(commit.header)}</td>"
            f"<td>{hyperlink_commit(repo_name, commit)}</td>"
            f"<td>{html.escape(commit.author)}</td>"
            f"<td>{html.escape(commit.hash)}</td>"
            "</tr>"
        )
        body_rows.append(row_html)

    body = "<tbody>\n" + "\n".join(body_rows) + "\n</tbody>"
    rows.append(body)

    return f"<table>{'\n'.join(rows)}</table>\n"


def generate_html(repos: dict[str, Repo]) -> None:
    """Generate an HTML report of the changes."""
    repo_rows = []

    row = "<h2>Summary</h2>\n"
    row += generate_versions_table(repos)
    repo_rows.append(row)

    for repo_name, repo in repos.items():
        row = f"<h2>{hyperlink_project(repo_name)} ({repo.old or 'n/a'} → {repo.new or 'n/a'})</h2>\n"

        if release_notes := hyperlink_release_notes(repo_name):
            row += f"<div>{release_notes}</div>"

        if not repo.commits:
            row += "<h4>No commits</h4>\n"
        else:
            row += generate_commit_table(repo_name, repo.commits)

        repo_rows.append(row)

    if contributors_html := generate_contributors_html(repos):
        repo_rows.append(contributors_html)

    html_content = HTML_TEMPLATE.replace("<!-- REPO_ROWS -->", "\n".join(repo_rows))

    with open("contributors.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info(
        f"Generated report: file://{pathlib.Path('contributors.html').absolute()}"
    )


# endregion


def get_libraries(project: str, old_ref: str, new_ref: str) -> dict[str, Repo]:
    """Get the new and old versions of each library."""
    libraries: dict[str, Repo] = {}
    for ref, attr in ((old_ref, "old"), (new_ref, "new")):
        logger.info(f"Getting {attr} {project} lockfile.")
        lock_file = get_uv_lock_file(project, ref)
        for pkg in lock_file:
            name = pkg.get("name")
            version = pkg.get("version")
            if name and LIBRARY_PATTERN.match(name):
                lib = libraries.setdefault(name, Repo())
                setattr(lib, attr, version)
    return libraries


def get_contributors(repos: dict[str, Repo]) -> list[str]:
    """Get a list of contributors, formatted for rst."""
    authors = {commit.author for repo in repos.values() for commit in repo.commits}
    return [
        f":literalref:`@{author} <https://github.com/{author}>`"
        for author in sorted(authors, key=str.lower)
    ]


def parse_repo_changes(repos: dict[str, Repo]) -> None:
    """Parse changes made in each repo.

    Updates repo dict in-place.
    """
    for name, repo in repos.items():
        if not repo.old or not repo.new:
            logger.debug(
                f"Not getting commits for {name} because it's missing version data."
            )
        elif repo.old == repo.new:
            logger.debug(f"Not getting commits for {name} because it wasn't updated.")
        else:
            repo.commits = get_commits(name, repo.old, repo.new)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    set_verbosity(args.verbose)

    repos: dict[str, Repo] = {args.project: Repo(old=args.old_ref, new=args.new_ref)}
    repos.update(get_libraries(args.project, args.old_ref, args.new_ref))

    parse_repo_changes(repos)

    if args.verbose:
        log_versions(repos)
        log_commits(repos)
        log_contributors(repos)

    generate_html(repos)
    return os.EX_OK


if __name__ == "__main__":
    raise SystemExit(main())
