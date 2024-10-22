# Linting Action

Lint your app with basic Makefile-based lint targets.

## Usage

An example job using this action:

```yaml
jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - uses: canonical/starflow/lint@main
```

## Requirements

This action expects your project to have a top-level Makefile containing at least the
following targets:

- `setup-lint`: This should install the linters on most systems.
- `lint`: This should run all linters.

The Makefile in this repository can be used as an example.
