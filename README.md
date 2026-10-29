# starflow

Starcraft team GHA Workflows

# Reusable Workflows

Some of these automations are provided as [Reusable workflows](https://docs.github.com/en/actions/sharing-automations/reusing-workflows).
For these workflows, you can embed them in a workflow you run at the `job` level.
Examples are provided below.

## Lint

The lint workflow installs and runs the relevant linters for the repository. It runs two jobs:

- `files`: Runs the code linters
- `docs`: Runs the documentation linters

The `docs` job only runs when a change touches the documentation. It expects the following
`make` targets:

- `setup-lint`: Installs relevant linters (only needs to work on Ubuntu)
- `lint-code`: Runs relevant linters
- `setup-docs`: Sets up the documentation environment
- `docs-lint`: Runs the documentation linters

The `source-files` input takes `"true"` or `"false"` and defaults to `"true"`. Pass `"false"` when the
change is documentation only, which skips the code linters.

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

The Python security scanner workflow uses [OSV-scanner](https://google.github.io/osv-scanner/)
to scan a Python project for security issues. It does the following:

1. Runs `uv export` to extract a project's requirements from its `uv.lock` file. The workflow can
   dictate the [export command's options](https://docs.astral.sh/uv/reference/cli/#uv-export) with
   the `uv-export-extra-args` input. The workflow can also exclude a dependency group by listing it
   in the `uv-export-no-groups` input.
2. Scans the exported requirements file for known vulnerabilities.
3. Recursively searches the project source tree for any other lockfiles.
4. Scans any found lockfiles for known vulnerabilities.

Exporting a `uv.lock` file can be disabled by setting `uv-export: false`.

### Usage

An example workflow for a Python project that excludes documentation dependencies from
the scan and suppresses findings from the `docs/` directory:

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
      # Include all dependency groups in the export, then exclude the docs groups.
      # The docs-sphinx-stack group must be defined in pyproject.toml.
      uv-export-extra-args: "--all-extras --all-groups"
      uv-export-no-groups: |
        docs
        docs-sphinx-stack
      # Exclude docs/ from the recursive source scan (e.g. to ignore example lockfiles).
      osv-exclude-paths: "docs/"
      # Pass additional arguments to osv-scanner, e.g. a project config file.
      osv-extra-args: "--config=osv-scanner.toml"
```

## Go security scanner

The Go security scanner workflow uses [OSV-scanner](https://google.github.io/osv-scanner/)
to scan a Go project for security issues. It recursively scans the project source tree for
known vulnerabilities in any lockfiles it finds.

### Usage

An example workflow for a Go project that excludes the `docs/` directory from the scan:

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
      # Exclude docs/ from the recursive source scan (e.g. to ignore example lockfiles).
      osv-exclude-paths: "docs/"
      # Pass additional arguments to osv-scanner, e.g. a project config file.
      osv-extra-args: "--config=osv-scanner.toml"
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

Additional environment variables (such as secrets) can be passed to the test runner using the
`extra-env-vars` input. This input takes a newline-separated list of `KEY=VALUE` pairs which will be
exported before the tests are run.

Due to GitHub Actions limitations, secrets cannot be passed directly into the `extra-env-vars`
string. Instead, you can map your secrets to generic slots (`secret-1` through `secret-10`) in the
`secrets` block of the call, and then reference them as `$SECRET_1` through `$SECRET_10` in
`extra-env-vars`.

Each of these test suites (fast, slow, or lowest) can be selectively disabled by passing an empty string
(`''`) to any of their platform or version inputs. This is useful for projects that only need a subset
of the testing suite.

An example workflow demonstrating secret mapping and selective skipping:

```yaml
name: Test Python
on:
  pull_request:

jobs:
  test:
    uses: canonical/starflow/.github/workflows/test-python.yaml@main
    secrets:
      secret-1: ${{ secrets.MY_SECRET_KEY }}
    with:
      # Disable slow tests by providing an empty platform list
      slow-test-platforms: ""
      extra-env-vars: | # Extra environment variables to pass to the tests
        MY_SECRET_KEY=$SECRET_1
        MY_VAR=value
```

## Documentation release

The documentation release workflow publishes a project's documentation to Read the Docs.
When triggered by a semantic versioning tag, it:

- Creates a `hotfix/<major>.<minor>` branch for minor versions.
- Syncs the Read the Docs versions and activates the new release, activating the
  version associated with the hotfix branch and setting it as the default.
- Creates redirects so that the major version points at the latest release.

It expects the version tag to follow the `<major>.<minor>.<patch>` format and requires a
Read the Docs API token, passed as a secret, and the Read the Docs project name, passed
as an input:

### Usage

An example workflow that uses this reusable workflow:

```yaml
name: Documentation release
on:
  push:
    tags:
      # These tags should be protected, remember to enable the rule:
      # https://github.com/canonical/starbase/settings/tag_protection
      - "[0-9]+.[0-9]+.[0-9]+"

jobs:
  docs-release:
    permissions:
      contents: write
    uses: canonical/starflow/.github/workflows/release-docs.yaml@main
    with:
      # TODO: set to your Read the Docs project slug.
      rtd-project: starbase
    secrets:
      RTD_TOKEN: ${{ secrets.RTD_TOKEN }}
```

# Other

## Renovate config

This repository also contains our base renovate configuration. A repository may be
configured to use this by adding the following to its `.github/renovate.json5` file:

```json5
{
  extends: ["github>canonical/starflow"],
}
```

## Contributor script

The `tools/contributors.py` script is used to generate a list of contributors for an application's release.
It also generates an HTML report of commits and changes to that application to aid in writing release notes.

Run `./tools/contributors.py --help` for usage and examples.
