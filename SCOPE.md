# Honest scope

What `pytest-mutation-verified` establishes, and what it does not.

## The question it answers

A regression test that has never failed is in one of two states, and they look identical from the
outside:

1. the defect it guards against genuinely cannot recur; or
2. the test stopped being able to detect that defect, and nobody noticed.

This plugin distinguishes them. You name the defect a test claims to catch, and the plugin
reintroduces it and checks that the test **fails**:

```python
@mutation_verified(
    target="mypkg.check_bounds",
    returns=True,
    description="bounds check always passes",
)
def test_oversized_read_is_refused():
    assert read(b"abc", 0, 99) is None
```

The test body runs twice: once against the mutated state, where it **must fail**, and once against
the real code, where it **must pass**. A test that passes in both states is reported as not
detecting the defect it claims to.

## What a pass means

> With `target` replaced as described, this test failed; with the real code, it passed.

That is a statement about **one mutation**, the one you named. It is a demonstration that the test is
wired to the code path it claims to cover, and that its assertions are load-bearing rather than
vacuous.

## What it does NOT mean

### It is not mutation testing

Mutation testing generates a large space of mutants and reports a kill rate. This plugin checks the
*specific* mutation you wrote down. There is no mutant generation, no operator set, and no score.

The trade is deliberate: a hand-named mutation is one you can read in the test, tied to the defect
that actually happened, and it costs one extra test run rather than thousands.

### It does not measure coverage or test quality

A test can be mutation-verified and still be a poor test — narrow, brittle, or checking the wrong
thing. All the plugin establishes is that it is *not vacuous* with respect to one named defect.

### It does not prove the defect cannot recur

It proves your test would notice **this** reintroduction. A different bug in the same function, or
the same bug reached by another path, is out of its reach.

### The mutation is a patch, not a semantic transformation

`target` is replaced by monkeypatching for the duration of the mutated run. Consequences:

- The target must be patchable by import path. Values already bound into another module's namespace
  at import time, C extensions, and inlined constants will not be affected.
- If the mutation does not actually change behaviour on the path your test exercises, the test will
  pass in both states and be reported as failing to detect — which is the correct answer, though the
  cause is your `target`, not your assertions.
- The mutated run executes your test body. If that body has side effects — writes files, mutates
  global state, talks to a network — they happen twice.

### It runs your test twice

Wall-clock cost is roughly double for decorated tests. Decorate the tests that guard against real
past defects, not every test you have.

## Requirements

The plugin must be **installed**, not merely importable, because it registers through a `pytest11`
entry point. Its own suite deliberately exercises the configuration a real user gets rather than a
`PYTHONPATH` shortcut — that is why `pip install -e .` is required for the tests to pass.

## When to use something else

| If you need | Use |
|---|---|
| A kill-rate score over generated mutants | `mutmut`, `cosmic-ray` |
| Line or branch coverage | `coverage.py` |
| A proof that a guard is correct, not that a test can fail | [certkit](https://github.com/nickharris808/certkit) |
| How many inputs escape an incorrect guard | [exploit-counter](https://github.com/nickharris808/exploit-counter) |

## The rest of the toolkit

This package shares no dependency with the others — it is the one piece that stands alone. It is here
because it answers the same underlying question from the testing side: *is this evidence actually
evidence?*

| | |
|---|---|
| **[certkit](https://github.com/nickharris808/certkit)** | the certificate format and the independent checker |
| **[exploit-counter](https://github.com/nickharris808/exploit-counter)** | if a guard is unsound, exactly how many states escape |
| **[crs-mcp](https://github.com/nickharris808/crs-mcp)** | the verdict surface AI agents call |
| **[soundnessbench](https://github.com/nickharris808/soundnessbench)** | the benchmark that grades soundness tools |

## The one-sentence version

pytest-mutation-verified shows that a named defect, reintroduced, makes a specific test fail — which
is evidence that the test is not vacuous, and is not evidence that the defect cannot recur.
