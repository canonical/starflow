# `teardown-caching`

This action stops the `pkgproxy` service and saves its payload cache at the end of a job.
Pair it with [`setup-python-runner`](../setup-python-runner/README.md).

## Example usage

```yaml
steps:
  - name: Set up runner
    id: setup-runner
    uses: canonical/starflow/setup-python-runner@main
    with:
      use-caching: true

  # ... job steps ...

  - name: Teardown caching
    if: always()
    uses: canonical/starflow/teardown-caching@main
    with:
      pkgproxy-cache-dir: ${{ steps.setup-runner.outputs.pkgproxy-cache-dir }}
      pkgproxy-cache-key-success: ${{ steps.setup-runner.outputs.pkgproxy-cache-key-success }}
      pkgproxy-cache-key-partial: ${{ steps.setup-runner.outputs.pkgproxy-cache-key-partial }}
      pkgproxy-cache-hit: ${{ steps.setup-runner.outputs.pkgproxy-cache-hit }}
```

## Inputs

### `pkgproxy-cache-dir`

The directory containing the `pkgproxy` payload cache (from `setup-python-runner`).

### `pkgproxy-cache-key-success`

The cache key to save under when the job succeeds (from `setup-python-runner`).

### `pkgproxy-cache-key-partial`

The cache key to save under when the job fails (from `setup-python-runner`).

### `pkgproxy-cache-hit`

Whether the success cache key was an exact hit (from `setup-python-runner`).

### `job-status`

The status of the job (`success`, `failure`, or `cancelled`). Defaults to `${{ job.status }}`.
