# starflow

Starcraft team GHA Workflows

# Reusable Workflows

Some of these automations are provided as [Reusable workflows](https://docs.github.com/en/actions/sharing-automations/reusing-workflows).
For these workflows, you can embed them in a workflow you run at the `job` level.
Examples are provided below.

## Lint

The lint workflow installs and runs the relevant linters for the repository. It expects the following
`make` targets:

- `setup-lint`: Installs relevant linters (only needs to work on Ubuntu)
- `lint`: Runs relevant linters

### Usage

An example workflow:

```yaml
name: QA
on:
  push:
    branches:
      - "main"
      - "feature/*"
      - "hotfix/*"
      - "release/*"
      - "renovate/*"
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: lengau/starflow/lint@work/CRAFT-3602/test-workflows
```

## Policy check

The policy check workflow checks that contributions to the project follow both Canonical corporate policy
and team policy. It checks:

- That the user has signed the Canonical CLA
- That commits follow [Starcraft team standards using Conventional Commits](https://github.com/canonical/starbase/blob/main/HACKING.rst#commits)

### Usage

An example workflow that uses this reusable workflow:

```yaml
name: Check policy
on:
  pull_request:

jobs:
  policy:
    uses: canonical/starflow/.github/workflows/policy.yaml@main
```

## Python security scanner

The Python security scanner workflow uses several tools (trivy, osv-scanner) to scan a
Python project for security issues. It does the following:

1. Creates a wheel of the project.
2. Exports a `uv.lock` file (if present in the project) as two requirements files:
   a. `requirements.txt` with no extras
   b. `requirements-all.txt` with all available extras

If there are any existing `requirements*.txt` files in your project, it will scan those
below too. Exporting a `uv.lock` file can be disabled by setting `uv-export: false`.

With [Trivy](https://github.com/aquasecurity/trivy), it:

1. Scans the requirements files
2. Scans the wheel file(s)
3. Scans the project directory
4. Installs each combination of (requirements, wheel) in a virtual environment and scans that environment.
5. If a `uv.lock` file exists for the project, creates a virtual environment using `uv sync` and
   scans that environment. `uv sync` can be configured with the `uv-sync-extra-args` input.

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

## Go security scanner

The Go security scanner workflow uses several tools (trivy, osv-scanner) to scan a
Go project for security issues.

### Usage

An example workflow for your own Go project that will use this workflow:

```yaml
name: Security scan
on:
  pull_request:
  push:
    branches:
      - main
      - hotfix/*

jobs:
  go-scans:
    name: Scan Go project
    uses: canonical/starflow/.github/workflows/scan-golang.yaml@main
    with:
      # Additional packages to install on the Ubuntu runners for building
      packages: protoc-gen-go-1-3
      # Additional arguments to pass to osv-scanner.
      # This example adds configuration from your project.
      osv-extra-args: "--config=.osv-scanner.toml"
      # Use the standard extra args and ignore spread tests
      trivy-extra-args: '--skip-dirs "tests/spread/**"'
```

## Python test runner

The Python test runner workflow uses GitHub workflows and `uv` to run Python tests in
several forms. It:

- Runs fast tests across multiple platforms and Python versions.
- Runs all tests on Ubuntu with the oldest supported python version and uv resolution
  set to `lowest`.
- Runs slow tests across their own set of platforms and Python versions.
- Uploads test coverage for tests as artefacts.

In order to do so, it expects the following `make` targets:

- `setup-tests`: Configures the system, installing any other necessary tools.
- `test-coverage`: Runs tests with test coverage. Fast and slow tests will use the
  `PYTEST_ADDOPTS` environment variable to run with or without the `slow` mark.

Because we use the snaps of [codespell](https://snapcraft.io/codespell),
[ruff](https://snapcraft.io/ruff) and [shellcheck](https://snapcraft.io/shellcheck)
frequently, this workflow installs those as well as uv.

An example workflow:

```yaml
name: Test Python
on:
  pull_request:

jobs:
  test:
    uses: canonical/starflow/.github/workflows/test-python.yaml@main
```

# Other Configuration

This repository also contains our base renovate configuration. A repository may be
configured to use this by adding the following to its `.github/renovate.json5` file:

```json5
{
  extends: ["github:canonical/starflow:renovate-base.json5"],
}
```
