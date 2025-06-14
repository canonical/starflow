# `setup-python-runner`

This action sets up runners for Python repositories. It updates apt (or homebrew),
installs `uv`, and otherwise prepares the runner.

## Example usage

This is used within the `test-python` workflow. To use it on its own:

```yaml
name: "Install latest LXD"
on: push
jobs:
  job1:
    runs-on: ubuntu-latest
    steps:
      - name: Set up runer
        uses: canonical/starflow/setup-python-runner@main
        with:
          lxd-channel: latest/edge
```

## Inputs

### `lxd-channel`

The snap channel from which to install LXD. Defaults to the current LTS channel.

### `python-version`

The version of Python to use with UV. If set, sets the `UV_PYTHON` environment variable
for the rest of the job.
