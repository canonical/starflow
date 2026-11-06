# `run-spread`

Runs spread and writes the test results to a JUnit XML file.

## Example usage

```yaml
- name: Run spread
  uses: canonical/starflow/run-spread@main
  with:
    args: ${{ matrix.spread-jobs }}

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v7
  with:
    name: test-results-${{ matrix.spread-jobs }}
    path: results/junit*.xml
    overwrite: true
```

The spread binary itself must be available on the runner in `PATH`.

## Inputs

### `args`

Arguments passed to spread, typically one or more job selections.

### `junit-name`

Disambiguates the JUnit file when a job runs spread more than once. Each
invocation writes `results/junit-<junit-name>.xml`. The whole
`results/junit*.xml` glob is uploaded as one artifact.

## JUnit mapping

- `classname` is the backend and system, such as `openstack:ubuntu-24.04-64`.
- `name` is the suite/task path, including any `:variant` suffix, such as
  `tests/spread/core24/foo:bar`.
- Failing tasks carry spread's error message as the failure text, including the
  `-----`-wrapped error block.
- Prepare and restore failures surface as their own failing test cases, such as
  `preparing:<context>`. This includes system-level failures like
  `preparing:openstack:ubuntu-24.04-64`.
- Tasks that spread reports as aborted become skipped test cases named `aborted-task-N`.
- For a restore failure, the task itself still gets its real (passing) outcome.
- A log with no recognizable content and a nonzero spread exit code produces
  a single `unparsed-spread-output` test case. With a zero-exit code, it produces
  an empty suite, which may happen if no tests ran, like when calling `spread -list`.

## Tests

```bash
uv run --with pytest pytest run-spread/tests
```
