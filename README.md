# starflow

Starcraft team GHA Workflows

# Reusable Workflows

Some of these automations are provided as [Reusable workflows](https://docs.github.com/en/actions/sharing-automations/reusing-workflows).
For these workflows, you can embed them in a workflow you run at the `job` level.
Examples are provided below.

## Python security scanner

The Python security scanner workflow uses several tools (trivy, osv-scanner) to scan a
Python project for security issues. It does the following:

1. Creates a wheel of the project.
2. Exports a `uv.lock` file (if present in the project) as two requirements files:
   a. `requirements.txt` with no extras
   b. `requirements-all.txt` with all available extras

If there are any existing `requirements*.txt` files in your project, it will scan those
below too.

With [Trivy](https://github.com/aquasecurity/trivy), it:

1. Scans the requirements files
2. Scans the wheel file(s)
3. Scans the project directory
4. Installs each combination of (requirements, wheel) in a virtual environment and scans that environment.

With [OSV-scanner](https://google.github.io/osv-scanner/) it:

1. Scans the requirements files
2. Scans the project directory

### Usage

An example workflow for your own Python project that will use this workflow:

```yaml
name: Security scan
on:
  pull_request:
  push:
    branches:
      - main
      - hotfix/*

jobs:
  python-scans:
    name: Scan Python project
    uses: canonical/starflow/.github/workflows/scan-python.yaml@main
    with:
      # Additional packages to install on the Ubuntu runners for building
      packages: python-apt-dev cargo
      # Additional arguments to `find` when finding requirements files.
      # This example ignores 'requirements-noble.txt'
      requirements-find-args: "! -name requirements-noble.txt"
      # Additional arguments to pass to osv-scanner.
      # This example adds configuration from your project.
      osv-extra-args: "--config=source/osv-scanner.toml"
      # Use the standard extra args and ignore spread tests
      trivy-extra-args: '--severity HIGH,CRITICAL --ignore-unfixed --skip-dirs "tests/spread/**"'
```
