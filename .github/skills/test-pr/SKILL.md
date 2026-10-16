---
name: test-pr
description: Test a starflow PR against all downstream team repositories by creating draft PRs pointing shared workflows to the PR branch and linking to test runs.
---

# Test PR (Downstream Integration Testing)

This skill helps developers test changes made in a `canonical/starflow` pull request against all team repositories that consume starflow's shared workflows and actions.

It automates:

1. Detecting the current starflow PR number, target branch/ref, and repository owner.
2. Finding all team repositories in `canonical` that use starflow workflows or actions.
3. For each downstream repository:
   - Creating a dedicated test branch `work/bot/starflow-test-pr-<PR_NUMBER>`.
   - Updating all `.github/workflows/*.yaml` references to point to the starflow PR branch.
   - Disabling non-starflow jobs using `if: false` to prevent unnecessary CI resource and CPU cycle usage without deleting files.
   - Pushing the branch and opening (or updating an existing) Draft PR titled `[DO NOT MERGE] Test starflow PR <PR_NUMBER>`.
4. Listing the resulting Draft PRs along with direct links to the triggered GitHub Actions workflow runs.
5. Providing cleanup capabilities once downstream testing is complete.

## When to Use

Invoke this skill when:

- The user asks to "test this PR", "test PR #123", or "test against downstream repositories".
- The user wants to verify whether a change to starflow's shared workflows/actions breaks any consuming projects (e.g. Snapcraft, Charmcraft, Rockcraft, Craft CLI, Craft Application, Craft Parts, Craft Providers, etc.).
- The user requests draft PRs to test workflow runs in team repositories.
- The user wants to clean up / close test PRs and branches created during previous test runs.

## Prerequisites

- `gh` CLI authenticated with repo write permissions (`gh auth status`).
- `git` and `python3` available in the environment.

## Usage & Execution

The skill includes a dedicated helper script located at `.github/skills/test-pr/test-downstream.py`.

### 1. Identify PR and Target Branch

Identify the starflow PR number and branch to test:

- If provided in the user prompt (e.g., "test PR 42" or "test PR on branch feature-xyz"), use that.
- Otherwise, run `gh pr view --json number,headRefName,headRepositoryOwner` or inspect `git branch --show-current`.

### 2. Execute Downstream Tester

Run the helper script from the repository root:

```bash
# Test across all downstream repositories in parallel
python3 .github/skills/test-pr/test-downstream.py --pr <PR_NUMBER> --workers 16

# Test and automatically update the starflow PR description with the results table
python3 .github/skills/test-pr/test-downstream.py --pr <PR_NUMBER> --update-pr-body

# Test with an explicit branch/ref or fork owner
python3 .github/skills/test-pr/test-downstream.py --pr <PR_NUMBER> --branch <BRANCH_NAME> --owner <OWNER>

# Test specific repositories only
python3 .github/skills/test-pr/test-downstream.py --pr <PR_NUMBER> --repos canonical/snapcraft canonical/charmcraft

# Dry run (verify workflow substitutions without pushing or creating PRs)
python3 .github/skills/test-pr/test-downstream.py --pr <PR_NUMBER> --dry-run
```

### 3. Present Results & Offer PR Body Update

Present the results to the user:

1. Display the rendered summary table with direct links to draft PRs and test workflow runs.
2. Provide a copy-pasteable raw markdown block containing the table.
3. Offer the user the choice to either copy the raw markdown or have the agent update the Starflow PR description automatically (or pass `--update-pr-body`).

Example output format:

```markdown
### Downstream Test PRs for Starflow PR #42

| Repository               | Draft PR                                                 | Test Workflow Runs                                                                                                                         |
| :----------------------- | :------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------- |
| **canonical/snapcraft**  | [#123](https://github.com/canonical/snapcraft/pull/123)  | [QA](https://github.com/canonical/snapcraft/actions/runs/1001), [Check policy](https://github.com/canonical/snapcraft/actions/runs/1002)   |
| **canonical/charmcraft** | [#456](https://github.com/canonical/charmcraft/pull/456) | [QA](https://github.com/canonical/charmcraft/actions/runs/1003), [Check policy](https://github.com/canonical/charmcraft/actions/runs/1004) |
| **canonical/rockcraft**  | [#789](https://github.com/canonical/rockcraft/pull/789)  | [QA](https://github.com/canonical/rockcraft/actions/runs/1005), [Check policy](https://github.com/canonical/rockcraft/actions/runs/1006)   |
```

### 4. Cleanup

When testing is finished or when requested by the user, close the draft PRs and delete the test branches:

```bash
python3 .github/skills/test-pr/test-downstream.py --pr <PR_NUMBER> --cleanup
```
