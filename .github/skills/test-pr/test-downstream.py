#!/usr/bin/env python3
"""
Test Starflow PRs against downstream repositories.

This script creates draft PRs in downstream team repositories pointing their
shared GitHub Actions workflows to a specific branch/PR of starflow, and lists
the resulting test workflow runs.
"""

from __future__ import annotations

import argparse
import concurrent.futures
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

import yaml

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


def get_starflow_pr_info(
    pr_number: str, owner: str = "canonical"
) -> Tuple[Optional[str], Optional[str]]:
    """Fetch headRefName and headRepositoryOwner login for a given Starflow PR number."""
    try:
        proc = run_cmd(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--repo",
                f"{owner}/starflow",
                "--json",
                "headRefName,headRepositoryOwner",
            ],
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            data = json.loads(proc.stdout)
            branch = data.get("headRefName")
            repo_owner = data.get("headRepositoryOwner", {}).get("login")
            return branch, repo_owner
    except Exception:
        pass
    return None, None


def discover_downstream_repos() -> List[str]:
    """Find team repositories in canonical org that use starflow in workflows."""
    repos = set()
    # 1. Query starcraft team repos via jq for robust line-by-line parsing
    try:
        proc = run_cmd(
            [
                "gh",
                "api",
                "orgs/canonical/teams/starcraft/repos",
                "--paginate",
                "--jq",
                ".[] | select(.archived == false and .private == false) | .full_name",
            ],
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            for line in proc.stdout.splitlines():
                full_name = line.strip()
                if full_name and full_name not in EXCLUDED_REPOS:
                    repos.add(full_name)
    except Exception:
        pass

    # 2. Add defaults if team query was empty
    if not repos:
        repos.update(DEFAULT_TEAM_REPOS)

    return sorted(repos)


def update_single_workflow_text(
    content: str, target_owner: str, target_ref: str
) -> Tuple[str, bool, List[str]]:
    """
    Update a single workflow YAML content.
    - Updates starflow references to target_owner/starflow@target_ref.
    - Adds `if: false` to non-starflow jobs to prevent unnecessary CI execution.
    Returns (new_content, uses_starflow, disabled_job_ids).
    """
    try:
        data = yaml.safe_load(content)
    except Exception:
        data = None

    if not isinstance(data, dict) or "jobs" not in data or not isinstance(data.get("jobs"), dict):
        return content, False, []

    jobs = data.get("jobs", {})
    starflow_jobs = set()
    non_starflow_jobs = set()

    for job_id, job_info in jobs.items():
        if not isinstance(job_info, dict):
            continue
        uses_sf = False
        if "uses" in job_info and "starflow" in str(job_info["uses"]):
            uses_sf = True
        for step in job_info.get("steps") or []:
            if isinstance(step, dict) and "uses" in step and "starflow" in str(step.get("uses")):
                uses_sf = True
                break
        if uses_sf:
            starflow_jobs.add(str(job_id))
        else:
            non_starflow_jobs.add(str(job_id))

    # 1. Update starflow references in text
    pattern = re.compile(
        r'(uses:\s*[\'"]?)[a-zA-Z0-9_.-]+/starflow(/[^@\s\r\n\'"]*)?@([^\s\r\n\'"]+)([\'"]?)'
    )
    new_content = pattern.sub(rf"\g<1>{target_owner}/starflow\g<2>@{target_ref}\g<4>", content)

    # 2. Add `if: false` to non-starflow jobs
    lines = new_content.splitlines()
    in_jobs = False
    current_job = None
    output_lines = []

    for line in lines:
        if re.match(r"^jobs:\s*(?:#.*)?$", line):
            in_jobs = True
            output_lines.append(line)
            continue
        if in_jobs:
            job_match = re.match(r"^  ([a-zA-Z0-9_.-]+):\s*(?:#.*)?$", line)
            if job_match:
                current_job = job_match.group(1)
                output_lines.append(line)
                if current_job in non_starflow_jobs:
                    output_lines.append("    if: false")
                continue
            elif re.match(r"^\S", line):
                in_jobs = False
                current_job = None
            elif current_job in non_starflow_jobs and re.match(r"^\s+if:\s*", line):
                continue
        output_lines.append(line)

    final_content = "\n".join(output_lines) + ("\n" if content.endswith("\n") else "")
    return final_content, len(starflow_jobs) > 0, sorted(non_starflow_jobs)


def update_workflows_in_dir(
    workflow_dir: Path, target_owner: str, target_ref: str
) -> Tuple[List[str], List[str]]:
    """
    Update workflow files in workflow_dir to point to target_owner/starflow at target_ref.
    Disables non-starflow jobs using `if: false` to save CI CPU cycles.
    Returns (starflow_workflow_files, disabled_jobs_summary).
    """
    starflow_files = []
    disabled_jobs_summary = []

    for yaml_path in sorted(list(workflow_dir.glob("*.yaml")) + list(workflow_dir.glob("*.yml"))):
        try:
            content = yaml_path.read_text(encoding="utf-8")
        except Exception:
            continue

        new_content, uses_sf, disabled_jobs = update_single_workflow_text(
            content, target_owner, target_ref
        )
        if uses_sf:
            starflow_files.append(yaml_path.name)
        if disabled_jobs:
            disabled_jobs_summary.append(f"{yaml_path.name} ({', '.join(disabled_jobs)})")

        if new_content != content:
            yaml_path.write_text(new_content, encoding="utf-8")

    return starflow_files, disabled_jobs_summary


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
    disabled_files: List[str] = None
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

            modified, disabled = update_workflows_in_dir(workflow_dir, target_owner, target_ref)
            if not modified:
                return RepoResult(
                    repo=repo,
                    status="skipped",
                    modified_files=[],
                    disabled_files=disabled,
                    error="No starflow workflow references found to update",
                )

            body = (
                f"This is an automated draft PR to test changes from starflow PR #{pr_number}.\n\n"
                f"- **Starflow PR**: https://github.com/canonical/starflow/pull/{pr_number}\n"
                f"- **Target Ref**: `{target_owner}/starflow@{target_ref}`\n"
                f"- **Starflow Workflows Tested**: {', '.join(modified)}\n"
                f"- **Disabled Non-Starflow Jobs (`if: false`)**: {', '.join(disabled) if disabled else 'none'}\n\n"
                f"⚠️ **DO NOT MERGE**: This PR is intended solely to verify downstream CI workflows."
            )

            if dry_run:
                return RepoResult(
                    repo=repo,
                    status="dry-run",
                    modified_files=modified,
                    disabled_files=disabled,
                    branch=branch_name,
                )

            # Create branch, commit, push
            run_cmd(["git", "checkout", "-b", branch_name], cwd=tmp_path)
            run_cmd(["git", "add", "-A", ".github/workflows"], cwd=tmp_path)

            commit_msg = (
                f"ci: test against starflow PR #{pr_number} ({target_ref})\n\n"
                f"[DO NOT MERGE] Point starflow workflows to {target_owner}/starflow@{target_ref}\n"
                f"Disabled non-starflow jobs (if: false): {', '.join(disabled) if disabled else 'none'}"
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

            # Check if an open PR already exists for testing this starflow PR
            existing_pr = None
            pr_view = run_cmd(
                ["gh", "pr", "view", head_spec, "--repo", repo, "--json", "url,number,state"],
                check=False,
            )
            if pr_view.returncode == 0 and pr_view.stdout.strip():
                try:
                    pr_data = json.loads(pr_view.stdout)
                    if pr_data.get("state") == "OPEN":
                        existing_pr = (pr_data.get("url"), pr_data.get("number"))
                except Exception:
                    pass

            if not existing_pr:
                pr_list_proc = run_cmd(
                    [
                        "gh",
                        "pr",
                        "list",
                        "--repo",
                        repo,
                        "--state",
                        "open",
                        "--head",
                        branch_name,
                        "--json",
                        "url,number",
                    ],
                    check=False,
                )
                if pr_list_proc.returncode == 0 and pr_list_proc.stdout.strip():
                    try:
                        pr_list_data = json.loads(pr_list_proc.stdout)
                        if pr_list_data:
                            existing_pr = (pr_list_data[0].get("url"), pr_list_data[0].get("number"))
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
                # Update title and body of existing PR
                run_cmd(
                    [
                        "gh",
                        "pr",
                        "edit",
                        str(pr_num),
                        "--repo",
                        repo,
                        "--title",
                        title,
                        "--body",
                        body,
                    ],
                    cwd=tmp_path,
                    check=False,
                )
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
                        disabled_files=disabled,
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


def format_markdown_table(successful: List[RepoResult], branch_name: str) -> str:
    """Format successful downstream test PR results into a markdown table."""
    lines = [
        "| Repository | Draft PR | Test Workflow Runs |",
        "| :--- | :--- | :--- |",
    ]
    for r in sorted(successful, key=lambda x: x.repo):
        runs_links = []
        if r.workflow_runs:
            for run in r.workflow_runs:
                name = run.get("name", "Workflow")
                url = run.get("url", "")
                runs_links.append(f"[{name}]({url})")
        if not runs_links:
            actions_url = f"https://github.com/{r.repo}/actions?query=branch%3A{branch_name}"
            runs_links.append(f"[All Action Runs]({actions_url})")

        runs_str = ", ".join(runs_links)
        lines.append(f"| **{r.repo}** | [#{r.pr_number}]({r.pr_url}) | {runs_str} |")
    return "\n".join(lines)


def update_starflow_pr_description(pr_number: str, table_md: str, owner: str = "canonical") -> bool:
    """Update or append the downstream test results table in the starflow PR description."""
    try:
        proc = run_cmd(
            ["gh", "pr", "view", str(pr_number), "--repo", f"{owner}/starflow", "--json", "body", "--jq", ".body"],
            check=False,
        )
        if proc.returncode != 0:
            return False
        current_body = proc.stdout.strip()

        section_header = "### Downstream Test PRs"
        if section_header in current_body:
            pattern = re.compile(r"### Downstream Test PRs.*?(?=\n### |\Z)", re.DOTALL)
            new_body = pattern.sub(f"{section_header}\n\n{table_md}", current_body).strip()
        else:
            new_body = f"{current_body}\n\n{section_header}\n\n{table_md}".strip()

        edit_proc = run_cmd(
            ["gh", "pr", "edit", str(pr_number), "--repo", f"{owner}/starflow", "--body", new_body],
            check=False,
        )
        return edit_proc.returncode == 0
    except Exception:
        return False


def cleanup_test_prs(repos: List[str], pr_number: str, branch_name: str, workers: int = 8) -> None:
    """Close test draft PRs and delete branches across repos in parallel."""
    print(f"Cleaning up test PRs and branches for starflow PR #{pr_number} ({len(repos)} repositories, workers={workers})...\n")

    def _cleanup_one(repo: str) -> None:
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
                    print(f"[{repo}] Closing draft PR #{pr_num}...")
                    run_cmd(["gh", "pr", "close", str(pr_num), "--repo", repo, "--delete-branch"], check=False)
                    print(f"[{repo}] Closed #{pr_num} and deleted branch.")
                    return
            except Exception:
                pass

        # Try deleting branch directly if PR didn't delete it
        del_proc = run_cmd(
            ["gh", "api", "-X", "DELETE", f"repos/{repo}/git/refs/heads/{branch_name}"],
            check=False,
        )
        if del_proc.returncode == 0:
            print(f"[{repo}] Deleted branch {branch_name}.")
        else:
            print(f"[{repo}] No branch or PR found to clean up.")

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(_cleanup_one, repos))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test starflow PRs across downstream repositories by creating draft PRs in parallel."
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
        default=None,
        help="Repository owner/fork hosting the starflow branch (default: auto-detected or canonical).",
    )
    parser.add_argument(
        "--repos",
        "-r",
        nargs="+",
        help="Specific downstream repos to test (e.g. canonical/snapcraft). Defaults to all team repos using starflow.",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=8,
        help="Number of concurrent workers for parallel cloning and PR creation (default: 8).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate workflow changes without pushing branches or creating PRs.",
    )
    parser.add_argument(
        "--update-pr-body",
        action="store_true",
        help="Automatically update/append the downstream test table into the Starflow PR description.",
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

    def log(msg: str = "") -> None:
        if args.json:
            print(msg, file=sys.stderr)
        else:
            print(msg)

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

    pr_head_branch = None
    pr_head_owner = None
    if pr_num:
        pr_head_branch, pr_head_owner = get_starflow_pr_info(
            pr_num, owner=args.owner or detected_owner or "canonical"
        )

    target_ref = args.branch or pr_head_branch or detected_branch or "main"
    target_owner = args.owner or pr_head_owner or detected_owner or "canonical"
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
        log("Discovering downstream repositories using starflow...")
        repos = discover_downstream_repos()

    if args.cleanup:
        cleanup_test_prs(repos, pr_num, branch_name, workers=args.workers)
        return 0

    log("==================================================")
    log("Starflow PR Downstream Testing")
    log(f"  PR Number   : #{pr_num}")
    log(f"  Target Ref  : {target_owner}/starflow@{target_ref}")
    log(f"  Test Branch : {branch_name}")
    log(f"  PR Title    : [DO NOT MERGE] Test starflow PR {pr_num}")
    log(f"  Repositories: {len(repos)} candidate repo(s)")
    log(f"  Concurrency : {args.workers} workers")
    if args.dry_run:
        log("  Mode        : DRY RUN (no git push or PR creation)")
    log("==================================================\n")

    results: List[RepoResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_repo = {
            executor.submit(
                process_repo,
                repo=repo,
                pr_number=pr_num,
                target_owner=target_owner,
                target_ref=target_ref,
                branch_name=branch_name,
                dry_run=args.dry_run,
            ): repo
            for repo in repos
        }
        for future in concurrent.futures.as_completed(future_to_repo):
            repo = future_to_repo[future]
            try:
                res = future.result()
                results.append(res)
                if res.status == "success":
                    log(f"  ✓ [{res.repo}] Draft PR ready: {res.pr_url} (tested: {', '.join(res.modified_files)})")
                elif res.status == "dry-run":
                    log(f"  ✓ [{res.repo}] [Dry Run] Would modify: {', '.join(res.modified_files)}")
                elif res.status == "skipped":
                    log(f"  - [{res.repo}] Skipped: {res.error}")
                else:
                    log(f"  ✗ [{res.repo}] Failed: {res.error}")
            except Exception as e:
                log(f"  ✗ [{repo}] Unexpected error: {e}")
                results.append(RepoResult(repo=repo, status="failed", modified_files=[], error=str(e)))

    if args.json:
        out_data = [
            {
                "repo": r.repo,
                "status": r.status,
                "modified_files": r.modified_files,
                "disabled_files": r.disabled_files or [],
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
        table_md = format_markdown_table(successful, branch_name)
        print("### Rendered Table:\n")
        print(table_md)

        print("\n### Raw Markdown (Copy & Paste):\n")
        print("```markdown")
        print("### Downstream Test PRs\n")
        print(table_md)
        print("```")

        if args.update_pr_body:
            print("\nUpdating Starflow PR description...")
            if update_starflow_pr_description(pr_num, table_md, target_owner):
                print(f"✓ Updated Starflow PR #{pr_num} description with downstream test table.")
            else:
                print(f"✗ Failed to update Starflow PR #{pr_num} description.")

        print("\n### Direct Links:")
        for r in sorted(successful, key=lambda x: x.repo):
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
