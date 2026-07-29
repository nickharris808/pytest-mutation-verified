# Troubleshooting

## `this test PASSED against the reintroduced defect`

The finding, not a bug. Your test passed both with and without the defect it claims to catch, so it
cannot detect that defect. Usually one of:

- The assertion is true either way (`assert isinstance(result, (bytes, type(None)))` holds whether or
  not the bounds check works).
- The mutation targets a different function from the one the test exercises.
- The code path is not reached at all with the arguments the test passes.

Fix the test, or fix the target. Removing the marker also makes it pass, and makes the test a claim
again.

## `cannot apply mutation to 'pkg.mod.func'`

The target string could not be resolved. It is an import path to the attribute being replaced,
resolved at call time — so it must name the module where the function is *looked up*, not
necessarily where it was defined. If `mod_b` does `from mod_a import check`, patching
`pkg.mod_a.check` will not affect `mod_b`'s reference.

## Every skipped test emits `PluggyTeardownRaisedWarning`

Fixed in 0.1.1. Upgrade. The hookwrapper read the wrapped test's outcome, which re-raised `Skipped`
during teardown; under `filterwarnings = error` that turned every skip in your project into an
error.

## The test body runs twice

By design: once mutated, once real. If your test is expensive, that doubles it. `--no-mutation-verify`
skips the mutated run for a fast local loop — and it reports that verification did not happen rather
than reporting the tests as verified.

## Side effects leak between the two runs

The mutated run executes your real test body. If it writes files, mutates module state, or talks to a
database, that happens twice and the second run may see the first one's leftovers. Use fixtures with
proper teardown; the plugin cannot undo effects it cannot see.

## `--mutation-require-all` fails on tests that should not have markers

It is a session-wide switch and intentionally blunt: it fails when *any* test function lacks a
marker. For gradual adoption, leave it off and add markers where they carry weight. A mutation-verified
test says one defect is caught; it is not a coverage metric and marking everything does not make it one.
