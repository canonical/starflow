# Coverage Action

Test a Python repository that uses uv

## Inputs

This action has the following inputs:

- `python-versions`: A string containing the python versions to run on, separated by
  spaces.
- `target`: The `make` target to run for testing. If a target other than `coverage` is
  specified, no code coverage artefact will be uploaded. (Default: `coverage`)
- `tics-token`: The token for TIOBE TICS. Normally stored in `${{ secrets.TICSAUTHTOKEN }}`

## Usage

An example job using this action:

```yaml
jobs:
  unit-tests:
    strategy:
      matrix:
        platform: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.platform }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Run tests
        uses: canonical/starflow/test-python@main
        with:
          python-versions: 3.8 3.10 3.12
          tics-token: ${{ secrets.TICSAUTHTOKEN }}
  integration-tests:
    strategy:
      matrix:
        platform: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.platform }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Run tests
        uses: canonical/starflow/test-python@main
        with:
          target: test-integration
```

## Requirements

This action expects your project to have a top-level Makefile containing at least the
following targets:

- `setup-tests`: This should configure your test environment.
- `coverage`: This should run the standard test suite and collect coverage into a
  `coverage.xml` file and an `htmlcov` directory.
