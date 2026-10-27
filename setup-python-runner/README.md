# `setup-python-runner`

This action sets up runners for Python repositories. It checks out the repository, optionally sets up
[`pkgproxy`](https://gitlab.com/zygoon/pkgproxy) on Linux runners for `apt` and `snap` caching,
updates apt (or homebrew), installs LXD and `uv`, and otherwise prepares the runner.

When `use-caching: true` is set, pair it with [`teardown-caching`](../teardown-caching/README.md) at
the end of a job to save the populated `pkgproxy` cache.

The package cache is keyed on the Linux distribution/release (from `/etc/os-release`), the runner
architecture, and the combined hash of `Makefile` and `common.mk` in the workspace.

## Example usage

This is used within the `test-python` workflow. To use it on its own:

```yaml
name: "Install latest LXD"
on: push
jobs:
  job1:
    runs-on: ubuntu-latest
    steps:
      - name: Set up runner
        id: setup-runner
        uses: canonical/starflow/setup-python-runner@main
        with:
          lxd-channel: latest/edge
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

### `use-lxd`

Whether to set up LXD on Linux runners. Defaults to `true`.

### `lxd-channel`

The snap channel from which to install LXD. Defaults to the current LTS channel.

### `python-version`

The version of Python to use with UV. If set, sets the `UV_PYTHON` environment variable
for the rest of the job.

### `use-caching`

Whether to set up `pkgproxy` caching on Linux runners. Defaults to `false`.

## Outputs

### `pkgproxy-cache-dir`

The directory containing the `pkgproxy` payload cache.

### `pkgproxy-cache-key-success`

The cache key to save under when the job succeeds.

### `pkgproxy-cache-key-partial`

The cache key to save under when the job fails.

### `pkgproxy-cache-hit`

`"true"` if the stable success cache key was an exact hit, otherwise `"false"` or empty.
