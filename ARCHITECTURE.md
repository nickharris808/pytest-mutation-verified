# Architecture

## The claim

A test that has never been observed to fail is not a regression test. It is a claim that some
behaviour holds, with no evidence that the test could tell you if it stopped holding.

This plugin makes that evidence mechanical: it reintroduces the defect a test says it catches and
asserts the test notices.

## How it works

```
@mutation_verified(target="pkg.check_bounds", returns=True)
def test_oversized_read_is_refused(): ...
```

For each marked test, `pytest_pyfunc_call` runs two phases:

1. **Mutated phase** — patch `target` to the described defect and run the test body. It must raise.
   If it passes, the test is reported as unable to detect the thing it exists to detect, and fails.
2. **Real phase** — remove the patch and let pytest run the test normally. It must pass.

A test that passes in both states is the interesting failure: it looks like coverage and is not.

## Design decisions

**The plugin wraps every test function, marked or not.** That is what makes an unmarked project
safe to install it into — and it is also why the hookwrapper must be invisible. Reading the wrapped
outcome re-raised `Skipped` inside hookwrapper teardown, which pluggy reports as
`PluggyTeardownRaisedWarning`; any project that merely had the plugin installed got that warning on
every skipped test, and an *error* under `filterwarnings = error`. pluggy propagates the outcome
itself, so the read was never needed.

**A patch that cannot be applied is a failure, not a skip.** `pytest.fail(pytrace=False)` names the
target. A mutation that silently did not apply would report a test as verified when nothing was
verified — the exact inversion this plugin exists to prevent.

**`--no-mutation-verify`** exists for a fast local loop, and it is a *reporting* switch: it does not
admit unverified tests as verified, it skips the mutated run entirely and says so.

**`--mutation-require-all`** fails a session where any test function lacks a marker. Off by default,
because a project adopting this gradually should not have to convert everything first.

## What it does not do

It does not generate mutations. You name the defect, because a generated mutation is a guess about
what could go wrong, and the whole value here is asserting a test catches the specific thing its
name claims. It also does not measure coverage: a mutation-verified test says one defect is caught,
not that the code is well tested.
