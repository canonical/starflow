# `ci-summary`

Triages PR CI failures with an LLM and posts a sticky summary comment.

## Example usage

```yaml
name: CI summary
on:
  workflow_run:
    workflows:
      - QA
      - Spread
      - Check policy
    types: [completed]
jobs:
  summary:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.event == 'pull_request' }}
    steps:
      - uses: canonical/starflow/ci-summary@main
        with:
          pr-number: ${{ github.event.workflow_run.pull_requests[0].number }}
          github-token: ${{ secrets.CRAFT_BOT_TOKEN }}
```

## Inputs

### `pr-number`

Pull request number to analyze.

### `github-token`

Token for a bot account with a Copilot seat; `GITHUB_TOKEN` won't work since it has no seat.

### `model`

AI model name for triage reasoning. Defaults to `claude-haiku-5.5`.

### `dry-run`

When `true`, prints the markdown output without posting a comment. Defaults to `false`.
