# Contributing to pytest-mutation-verified

## Test the plugin the way a user experiences it

All tests use pytest's `pytester` fixture, which runs a real pytest session in a temp directory and
lets you assert on the reported outcome. Do not test the plugin's internals — test what a run
prints and what it exits with. A plugin is a user-facing behaviour, not a set of functions.

```bash
pip install -e ".[dev]"
pytest
```

## The invariant: refusing must stay possible

The load-bearing test is `test_a_test_that_cannot_fail_is_rejected`. A plugin that never refuses
anything would pass every other test in the suite while being completely useless. If you change the
detection logic, that test must still fail the weak test — check it deliberately rather than
trusting a green run.

## The escape hatch must never lie

`--no-mutation-verify` suppresses the mutated run. When it is set the plugin must make **no claim**:
no summary line, no "verified" marker. A flag that turns verification off must not leave behind
output that reads as though verification happened.

## Adding a mutation form

New forms (source-level patching, parametrised mutations) are welcome. They need:

- a `pytester` test showing detection succeeds on a real test;
- a `pytester` test showing detection *fails* on a test that cannot see the defect;
- a README note if the form has a caveat a user would otherwise hit.

Anything listed in the README's Roadmap section is fair game and unclaimed.

## License

Contributions are accepted under Apache-2.0.
