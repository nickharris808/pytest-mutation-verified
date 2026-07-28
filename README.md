# pytest-mutation-verified

[![ci](https://github.com/nickharris808/pytest-mutation-verified/actions/workflows/ci.yml/badge.svg)](https://github.com/nickharris808/pytest-mutation-verified/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![status](https://img.shields.io/badge/status-pre--release-orange.svg)](#install)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**Your regression test has never failed. Are you sure it can?**

You fix a bug. You write a regression test. It passes. You ship.

But you never ran that test against the *broken* code. If the test is subtly wrong — asserts the
wrong thing, exercises a different path, a fixture masks the condition — it passes on the fixed code
and would have passed on the broken code too. It is not a regression test. It is a decoration that
costs CI time and buys nothing.

This plugin makes the missing step mandatory.

<a id="install"></a>
```bash
pip install "pytest-mutation-verified@git+https://github.com/nickharris808/pytest-mutation-verified@main"
```

> **Pre-release.** The PyPI name is reserved and publication is imminent; until then the line above
> is the working install. It is tested in CI on Linux, macOS, and Windows.

## 30-second quickstart

Mark a test with the defect it claims to catch:

```python
from pytest_mutation_verified import mutation_verified
from mypkg import read

@mutation_verified(
    target="mypkg.check_bounds",     # reintroduce the defect here
    returns=True,                     # by making the bounds check always pass
    description="bounds check always passes",
)
def test_oversized_read_is_refused():
    assert read(b"abc", 0, 99) is None
```

The plugin now runs the test body **twice**:

1. against the mutated (broken) state — the test **must fail**;
2. against the real code — the test **must pass**.

A test that passes in both states is refused:

```
.F                                                                       [100%]
=================================== FAILURES ===================================
________________________ test_that_cannot_actually_fail ________________________
mutation-verified: this test PASSED against the reintroduced defect (mutation of
mypkg.check_bounds), so it cannot detect the thing it exists to catch. The test
is not a regression test until it has been observed to fail.
------------------------------ mutation-verified -------------------------------
1 of 2 mutation(s) detected by their tests
  NOT DETECTED: test_demo.py::test_that_cannot_actually_fail -> mypkg.check_bounds
=========================== short test summary info ============================
1 failed, 1 passed in 0.08s
```

That output is copied from a real run of the bundled example, not typed by hand.

## Why not just use a mutation-testing tool?

Mutation testing (mutmut, cosmic-ray) mutates your *source* broadly and reports a survival score
across the suite. It is excellent and it is slow, and the score is a suite-level aggregate.

This plugin does something narrower and cheaper. It does not search for mutations — **you name the
one defect that matters**, the one the test was written for. It runs in the same session as your
normal suite with no extra pass, and it makes a per-test binary claim: *this specific test detects
this specific defect*. Use both; they answer different questions.

## The two forms

```python
# Patch to a constant return value
@mutation_verified(target="mypkg.check_bounds", returns=True)

# Patch to a callable, for a more surgical defect
@mutation_verified(
    target="mypkg.check_bounds",
    replacement=lambda off, length, cap: off + length <= cap + 1,  # off-by-one
    description="off-by-one in the capacity comparison",
)
```

Stack the decorator to require detection of several defects by the same test. All of them must be
detected.

## Options

| Flag | Effect |
|---|---|
| `--no-mutation-verify` | skip the mutated run entirely |
| `--mutation-require-all` | fail the session if any test function carries no marker |

`--no-mutation-verify` is an escape hatch for a broken environment, not a way to pass. When it is
set the plugin makes **no claim at all** — the summary line disappears rather than reporting tests as
verified. Nothing is silently admitted.

## Honest scope

- **This verifies detection, not correctness.** A test can detect the mutation and still assert
  something weaker than you intended. Mutation-verification is a floor, not a ceiling.
- **The mutation is only as good as you make it.** `returns=True` on a predicate is a blunt
  instrument; a `replacement` that reproduces the *original* bug is far stronger evidence.
- **Patching is `unittest.mock.patch`.** It rebinds a dotted path, so it cannot reach code that
  captured the reference at import time. If your test does not detect a mutation you believe is
  real, check that the call site resolves the name at call time.
- **Fixtures are passed through unchanged** to the mutated run, so a fixture with side effects runs
  twice. Session-scoped fixtures are created once, as usual.

`--mutation-require-all` is per *function*, not per collected item, so a parametrised test with five
cases is reported once rather than five times.

## Roadmap (not yet implemented)

- Source-level mutation (patching an AST node rather than a dotted name) would remove the
  import-time-binding caveat above.

Listed here rather than in the feature table because it does not work yet.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

15 tests, run through pytest's own `pytester` fixture — real pytest sessions in a temp directory,
asserting on what an actual run reports. The load-bearing test is
`test_a_test_that_cannot_fail_is_rejected`: a plugin that never refuses anything would pass every
other test in the file.

## Documentation

| | |
|---|---|
| [`SCOPE.md`](SCOPE.md) | what a mutation-verified test establishes, and what it does not |

## The rest of the toolkit

| | |
|---|---|
| **[certkit](https://github.com/nickharris808/certkit)** | the certificate format and the independent checker |
| **[exploit-counter](https://github.com/nickharris808/exploit-counter)** | if a guard is unsound, exactly how many states escape |
| **[crs-mcp](https://github.com/nickharris808/crs-mcp)** | the verdict surface AI coding agents call, over MCP |
| **[soundnessbench](https://github.com/nickharris808/soundnessbench)** | the benchmark that grades all of the above |
| **[certkit-action](https://github.com/nickharris808/certkit-action)** | run the check in your CI |
| **[pytest-mutation-verified](https://github.com/nickharris808/pytest-mutation-verified)** | prove your regression test can actually fail |
| **[cve-proof-corpus](https://huggingface.co/datasets/nickh007/cve-proof-corpus)** | six real CVEs with machine-checkable proofs |
| **[Try it in your browser](https://huggingface.co/spaces/nickh007/certkit-demo)** | no install; watch a forgery get refused |

## License

Apache-2.0. This one has no moat and is not meant to have one — it is useful to everybody and costs
us nothing.

---

Part of **[certified discovery](https://nickharris808.github.io/certified-discovery/)** — ten artifacts built on one asymmetry: checking a proof is cheap and auditable, so the thing that produced it does not have to be trusted.
