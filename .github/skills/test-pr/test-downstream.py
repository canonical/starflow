#!/usr/bin/env python3
"""
Test Starflow PRs against downstream repositories.

This script creates draft PRs in downstream team repositories pointing their
shared GitHub Actions workflows to a specific branch/PR of starflow, and lists
the resulting test workflow runs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple

EXCLUDED_REPOS = {
    "canonical/starflow",
    "canonical/ulwazi",
    "canonical/craft-artifacts",
}

DEFAULT_TEAM_REPOS = [
    "canonical/snapcraft",
    "canonical/charmcraft",
    "canonical/rockcraft",
    "canonical/craft-application",
    "canonical/craft-cli",
    "canonical/craft-parts",
    "canonical/craft-providers",
    "canonical/craft-store",
    "canonical/craft-grammar",
    "canonical/starbase",
    "canonical/debcraft",
    "canonical/sdkcraft",
    "canonical/imagecraft",
    "canonical/sourcecraft",
    "canonical/bld",
]


def run_cmd(
    cmd: List[str],
    cwd: Optional[Path] = None,
    check: bool = True,
    capture_output: bool = True,
    text: bool = True,
    env: Optional[dict] = None,
) -> subprocess.CompletedProcess:
    """Run a command safely and return CompletedProcess."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        capture_output=capture_output,
        text=text,
        env=full_env,
    )


def get_current_starflow_pr_or_branch() -> Tuple[Optional[str], str, str]:
    """
    Detect starflow PR number, target ref/branch, and owner.
    Returns (pr_number, branch_ref, owner).
    """
    # Try getting PR info from gh pr view
    try:
        proc = run_cmd(["gh", "pr", "view", "--json", "number,headRefName,headRepositoryOwner"], check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            data = json.loads(proc.stdout)
            pr_num = str(data.get("number"))
            branch = data.get("headRefName")
            owner = data.get("headRepositoryOwner", {}).get("login", "canonical")
            if pr_num and branch:
                return pr_num, branch, owner
    except Exception:
        pass

    # Fallback to current git branch
    try:
        proc = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=False)
        if proc.returncode == 0:
            branch = proc.stdout.strip()
            # If branch is like work/123-fix or pr-123 or similar, attempt to extract number
            num_match = re.search(r"(?:pr[-/]?|#)(\d+)", branch, re.IGNORECASE)
            pr_num = num_match.group(1) if num_match else None
            return pr_num, branch, "canonical"
    except Exception:
        pass

    return None, "main", "canonical"


def discover_downstream_repos() -> List[str]:
    """Find team repositories in canonical org that use starflow in workflows."""
    repos = set()
    # 1. Query starcraft team repos
    try:
        proc = run_cmd(
            ["gh", "api", "orgs/canonical/teams/starcraft/repos", "--paginate"],
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            for line in proc.stdout.splitlines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict):
                            full_name = item.get("full_name")
                            archived = item.get("archived", False)
                            private = item.get("private", False)
                            # Exclude starflow itself, private repos, archived repos, and excluded repos
                            if (
                                full_name
                                and full_name not in EXCLUDED_REPOS
                                and not archived
                                and not private
                            ):
                                repos.add(full_name)
                except Exception:
                    continue
    except Exception:
        pass

    # 2. Add defaults if team query was empty
    if not repos:
        repos.update(DEFAULT_TEAM_REPOS)

    return sorted(repos)


def update_workflows_in_dir(workflow_dir: Path, target_owner: str, target_ref: str) -> List[str]:
    """
    Update workflow files in workflow_dir to point to target_owner/starflow at target_ref.
    Returns list of modified file names.
    """
    modified_files = []
    # Pattern to match: uses: <any_owner>/starflow(/path)?@<old_ref>
    # Captures: 1=quote if any, 2=subpath if any, 3=old_ref
    pattern = re.compile(
        r'(uses:\s*[\'"]?)[a-zA-Z0-9_.-]+/starflow(/[^@\s\r\n\'"]*)?@([^\s\r\n\'"]+)([\'"]?)'
    )

    for yaml_path in list(workflow_dir.glob("*.yaml")) + list(workflow_dir.glob("*.yml")):
        try:
            content = yaml_path.read_text(encoding="utf-8")
        except Exception:
            continue

        def repl(match: re.Match) -> str:
            prefix = match.group(1)
            subpath = match.group(2) or ""
            suffix = match.group(4) or ""
            return f"{prefix}{target_owner}/starflow{subpath}@{target_ref}{suffix}"

        new_content, count = pattern.subn(repl, content)
        if count > 0 and new_content != content:
            yaml_path.write_text(new_content, encoding="utf-8")
            modified_files.append(yaml_path.name)

    return modified_files


def get_gh_user() -> Optional[str]:
    """Get authenticated GitHub username."""
    try:
        proc = run_cmd(["gh", "api", "user", "--jq", ".login"], check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return None


@dataclass
class RepoResult:
    repo: str
    status: str
    modified_files: List[str]
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    branch: Optional[str] = None
    workflow_runs: List[dict] = None
    error: Optional[str] = None


def process_repo(
    repo: str,
    pr_number: str,
    target_owner: str,
    target_ref: str,
    branch_name: str,
    dry_run: bool = False,
) -> RepoResult:
    """Clone downstream repo, update workflows, push branch and create/update Draft PR."""
    repo_name = repo.split("/")[-1]
    title = f"[DO NOT MERGE] Test starflow PR {pr_number}"
    body = (
        f"This is an automated draft PR to test changes from starflow PR #{pr_number}.\n\n"
        f"- **Starflow PR**: https://github.com/canonical/starflow/pull/{pr_number}\n"
        f"- **Target Ref**: `{target_owner}/starflow@{target_ref}`\n\n"
        f"⚠️ **DO NOT MERGE**: This PR is intended solely to verify downstream CI workflows."
    )

    with tempfile.TemporaryDirectory(prefix=f"starflow-test-{repo_name}-") as tmpdir:
        tmp_path = Path(tmpdir)
        try:
            # Clone default branch
            clone_proc = run_cmd(
                ["gh", "repo", "clone", repo, str(tmp_path)],
                check=False,
            )
            if clone_proc.returncode != 0:
                return RepoResult(
                    repo=repo,
                    status="failed",
                    modified_files=[],
                    error=f"Failed to clone: {clone_proc.stderr.strip()}",
                )

            workflow_dir = tmp_path / ".github" / "workflows"
            if not workflow_dir.is_dir():
                return RepoResult(
                    repo=repo,
                    status="skipped",
                    modified_files=[],
                    error="No .github/workflows directory found",
                )

            modified = update_workflows_in_dir(workflow_dir, target_owner, target_ref)
            if not modified:
                return RepoResult(
                    repo=repo,
                    status="skipped",
                    modified_files=[],
                    error="No starflow workflow references found to update",
                )

            if dry_run:
                return RepoResult(
                    repo=repo,
                    status="dry-run",
                    modified_files=modified,
                    branch=branch_name,
                )

            # Create branch, commit, push
            run_cmd(["git", "checkout", "-b", branch_name], cwd=tmp_path)
            for m in modified:
                run_cmd(["git", "add", f".github/workflows/{m}"], cwd=tmp_path)

            commit_msg = (
                f"ci: test against starflow PR #{pr_number} ({target_ref})\n\n"
                f"[DO NOT MERGE] Point starflow workflows to {target_owner}/starflow@{target_ref}"
            )
            run_cmd(["git", "commit", "-m", commit_msg], cwd=tmp_path)

            # Push branch (try origin first, fall back to personal fork if write access restricted)
            push_proc = run_cmd(["git", "push", "-u", "origin", branch_name, "--force"], cwd=tmp_path, check=False)
            head_spec = branch_name
            if push_proc.returncode != 0:
                user_login = get_gh_user()
                if user_login:
                    run_cmd(["gh", "repo", "fork", repo, "--default-branch-only", "--clone=false"], check=False)
                    fork_remote = f"git@github.com:{user_login}/{repo_name}.git"
                    run_cmd(["git", "remote", "add", "user-fork", fork_remote], cwd=tmp_path, check=False)
                    push_fork = run_cmd(["git", "push", "-u", "user-fork", branch_name, "--force"], cwd=tmp_path, check=False)
                    if push_fork.returncode == 0:
                        head_spec = f"{user_login}:{branch_name}"
                    else:
                        return RepoResult(
                            repo=repo,
                            status="failed",
                            modified_files=modified,
                            error=f"Push failed to origin and fork: {push_fork.stderr.strip()}",
                        )
                else:
                    return RepoResult(
                        repo=repo,
                        status="failed",
                        modified_files=modified,
                        error=f"Failed to push branch: {push_proc.stderr.strip()}",
                    )

            # Check if PR already exists for this branch
            existing_pr = None
            pr_view = run_cmd(
                ["gh", "pr", "view", head_spec, "--repo", repo, "--json", "url,number"],
                check=False,
            )
            if pr_view.returncode == 0 and pr_view.stdout.strip():
                try:
                    pr_data = json.loads(pr_view.stdout)
                    existing_pr = (pr_data.get("url"), pr_data.get("number"))
                except Exception:
                    pass

            # Get default branch
            default_branch = "main"
            def_proc = run_cmd(
                ["gh", "repo", "view", repo, "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"],
                check=False,
            )
            if def_proc.returncode == 0 and def_proc.stdout.strip():
                default_branch = def_proc.stdout.strip()

            pr_url = None
            pr_num = None
            if existing_pr:
                pr_url, pr_num = existing_pr
            else:
                # Create draft PR (retry once if ref indexing has a slight delay)
                for attempt in range(3):
                    if attempt > 0:
                        time.sleep(2.0)
                    create_pr = run_cmd(
                        [
                            "gh",
                            "pr",
                            "create",
                            "--repo",
                            repo,
                            "--draft",
                            "--title",
                            title,
                            "--body",
                            body,
                            "--base",
                            default_branch,
                            "--head",
                            head_spec,
                        ],
                        cwd=tmp_path,
                        check=False,
                    )
                    if create_pr.returncode == 0 and create_pr.stdout.strip():
                        pr_url = create_pr.stdout.strip().splitlines()[-1]
                        match = re.search(r"/pull/(\d+)", pr_url)
                        if match:
                            pr_num = int(match.group(1))
                        break
                if not pr_url:
                    return RepoResult(
                        repo=repo,
                        status="failed",
                        modified_files=modified,
                        error=f"Failed to create draft PR: {create_pr.stderr.strip()}",
                    )

            # Fetch workflow runs
            workflow_runs = fetch_workflow_runs(repo, branch_name)

            return RepoResult(
                repo=repo,
                status="success",
                modified_files=modified,
                pr_url=pr_url,
                pr_number=pr_num,
                branch=branch_name,
                workflow_runs=workflow_runs,
            )

        except Exception as e:
            return RepoResult(
                repo=repo,
                status="failed",
                modified_files=[],
                error=str(e),
            )


def fetch_workflow_runs(repo: str, branch: str, retries: int = 3, delay: float = 3.0) -> List[dict]:
    """Fetch recent workflow runs for a branch in a repo."""
    runs = []
    for attempt in range(retries):
        if attempt > 0:
            time.sleep(delay)
        proc = run_cmd(
            [
                "gh",
                "run",
                "list",
                "--repo",
                repo,
                "--branch",
                branch,
                "--limit",
                "10",
                "--json",
                "databaseId,name,url,status,conclusion,event",
            ],
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                data = json.loads(proc.stdout)
                if data:
                    runs = data
                    break
            except Exception:
                pass
    return runs


def cleanup_test_prs(repos: List[str], pr_number: str, branch_name: str) -> None:
    """Close test draft PRs and delete branches across repos."""
    print(f"Cleaning up test PRs and branches for starflow PR #{pr_number}...")
    for repo in repos:
        print(f"\n[{repo}]")
        # Check for open PR on branch
        proc = run_cmd(
            ["gh", "pr", "view", branch_name, "--repo", repo, "--json", "number,url,state"],
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                data = json.loads(proc.stdout)
                pr_num = data.get("number")
                state = data.get("state")
                if pr_num and state == "OPEN":
                    print(f"  Closing draft PR #{pr_num}...")
                    run_cmd(["gh", "pr", "close", str(pr_num), "--repo", repo, "--delete-branch"], check=False)
                    print(f"  Closed #{pr_num} and requested branch deletion.")
                    continue
            except Exception:
                pass

        # Try deleting branch directly if PR didn't delete it
        del_proc = run_cmd(
            ["gh", "api", "-X", "DELETE", f"repos/{repo}/git/refs/heads/{branch_name}"],
            check=False,
        )
        if del_proc.returncode == 0:
            print(f"  Deleted branch {branch_name}.")
        else:
            print("  No branch or PR found to clean up.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test starflow PRs across downstream repositories by creating draft PRs."
    )
    parser.add_argument(
        "--pr",
        "-p",
        help="Starflow PR number (e.g. 42 or #42) or URL. If omitted, detected automatically.",
    )
    parser.add_argument(
        "--branch",
        "-b",
        help="Starflow branch or ref to test. If omitted, detected from PR or current git branch.",
    )
    parser.add_argument(
        "--owner",
        "-o",
        default="canonical",
        help="Repository owner/fork hosting the starflow branch (default: canonical).",
    )
    parser.add_argument(
        "--repos",
        "-r",
        nargs="+",
        help="Specific downstream repos to test (e.g. canonical/snapcraft). Defaults to all team repos using starflow.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate workflow changes without pushing branches or creating PRs.",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Close draft PRs and delete test branches created for the specified PR.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON results.",
    )

    args = parser.parse_args()

    # Determine PR number, branch, owner
    detected_pr, detected_branch, detected_owner = get_current_starflow_pr_or_branch()

    pr_num = args.pr or detected_pr
    if pr_num:
        # Normalize "#123" or URL to just number string
        match = re.search(r"(\d+)", str(pr_num))
        pr_num = match.group(1) if match else str(pr_num)
    else:
        print("Error: Could not determine starflow PR number. Please pass --pr <number>.", file=sys.stderr)
        return 1

    target_ref = args.branch or detected_branch
    target_owner = args.owner or detected_owner
    branch_name = f"work/bot/starflow-test-pr-{pr_num}"

    # Determine target repos
    if args.repos:
        repos = []
        for r in args.repos:
            for item in r.split(","):
                item = item.strip()
                if item:
                    if "/" not in item:
                        item = f"canonical/{item}"
                    repos.append(item)
    else:
        print("Discovering downstream repositories using starflow...")
        repos = discover_downstream_repos()

    if args.cleanup:
        cleanup_test_prs(repos, pr_num, branch_name)
        return 0

    print(f"==================================================")
    print(f"Starflow PR Downstream Testing")
    print(f"  PR Number   : #{pr_num}")
    print(f"  Target Ref  : {target_owner}/starflow@{target_ref}")
    print(f"  Test Branch : {branch_name}")
    print(f"  PR Title    : [DO NOT MERGE] Test starflow PR {pr_num}")
    print(f"  Repositories: {len(repos)} candidate repo(s)")
    if args.dry_run:
        print(f"  Mode        : DRY RUN (no git push or PR creation)")
    print(f"==================================================\n")

    results: List[RepoResult] = []

    for idx, repo in enumerate(repos, 1):
        print(f"[{idx}/{len(repos)}] Processing {repo}...")
        res = process_repo(
            repo=repo,
            pr_number=pr_num,
            target_owner=target_owner,
            target_ref=target_ref,
            branch_name=branch_name,
            dry_run=args.dry_run,
        )
        results.append(res)
        if res.status == "success":
            print(f"  ✓ Draft PR created: {res.pr_url}")
            print(f"    Modified workflows: {', '.join(res.modified_files)}")
        elif res.status == "dry-run":
            print(f"  ✓ [Dry Run] Would modify: {', '.join(res.modified_files)}")
        elif res.status == "skipped":
            print(f"  - Skipped: {res.error}")
        else:
            print(f"  ✗ Failed: {res.error}")

    if args.json:
        out_data = [
            {
                "repo": r.repo,
                "status": r.status,
                "modified_files": r.modified_files,
                "pr_url": r.pr_url,
                "pr_number": r.pr_number,
                "branch": r.branch,
                "workflow_runs": r.workflow_runs or [],
                "error": r.error,
            }
            for r in results
        ]
        print(json.dumps(out_data, indent=2))
        return 0

    # Print Markdown Summary
    successful = [r for r in results if r.status == "success"]
    failed = [r for r in results if r.status == "failed"]
    skipped = [r for r in results if r.status == "skipped"]

    print("\n" + "=" * 50)
    print("## Summary of Downstream PRs & Test Workflow Runs")
    print("=" * 50 + "\n")

    if successful:
        print("| Repository | Draft PR | Workflow Runs / Actions |")
        print("| :--- | :--- | :--- |")
        for r in successful:
            runs_links = []
            if r.workflow_runs:
                for run in r.workflow_runs:
                    name = run.get("name", "Workflow")
                    url = run.get("url", "")
                    status = run.get("status", "")
                    runs_links.append(f"[{name}]({url}) ({status})")
            if not runs_links:
                actions_url = f"https://github.com/{r.repo}/actions?query=branch%3A{branch_name}"
                runs_links.append(f"[All Action Runs]({actions_url})")

            runs_str = "<br>".join(runs_links)
            print(f"| **{r.repo}** | [{r.repo}#{r.pr_number}]({r.pr_url}) | {runs_str} |")

        print("\n### Direct Links:")
        for r in successful:
            print(f"\n#### {r.repo}")
            print(f"- **Draft PR**: {r.pr_url}")
            if r.workflow_runs:
                for run in r.workflow_runs:
                    name = run.get("name", "Workflow")
                    url = run.get("url", "")
                    status = run.get("status", "")
                    print(f"  - [{name}] {url} ({status})")
            else:
                actions_url = f"https://github.com/{r.repo}/actions?query=branch%3A{branch_name}"
                print(f"  - Actions overview: {actions_url}")
    elif args.dry_run:
        print(f"Dry run complete. {len([r for r in results if r.status == 'dry-run'])} repository(ies) would be updated.")
    else:
        print("No draft PRs were created.")

    if failed:
        print("\n### Errors / Failures:")
        for r in failed:
            print(f"- **{r.repo}**: {r.error}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
