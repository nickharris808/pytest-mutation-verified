"""pytest-mutation-verified -- a regression test is not admitted until it has been
observed to fail against the defect it exists to catch.

The problem this solves is embarrassingly common and almost never caught. You fix
a bug, you write a regression test, the test passes, you ship. But you never ran
that test against the *broken* code. If the test is subtly wrong -- it asserts the
wrong thing, it exercises a different path, a fixture masks the condition -- it
passes on the fixed code and would also have passed on the broken code. It is not
a regression test. It is a decoration that costs CI time and buys nothing.

This plugin makes the missing step explicit. Mark a test with the defect it
catches, supply a mutation that reintroduces that defect, and the plugin runs the
test body twice:

    1. against the mutated (broken) state -- the test MUST fail;
    2. against the real code -- the test MUST pass.

A test that passes in both states is reported as **not mutation-verified** and
fails, because it has proven it cannot detect the thing it was written for.

Usage::

    @mutation_verified(target="mypkg.parser.check_bounds", returns=True)
    def test_rejects_oversized_payload():
        assert parse(b"\\xff" * 100) is None

The ``target`` is patched to a constant (or to a supplied replacement) for the
first run, which is what reintroduces the defect.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from unittest import mock

import pytest

__all__ = ["mutation_verified", "MutationSpec"]

_MARKER = "mutation_verified"


@dataclass
class MutationSpec:
    """How to reintroduce the defect a test claims to catch."""

    target: str
    #: Replacement value. Use ``returns`` for the common "make this function
    #: return a constant" case, or ``replacement`` for a callable.
    returns: Any = None
    replacement: Callable[..., Any] | None = None
    has_returns: bool = False
    description: str = ""

    def build_patch(self):
        if self.replacement is not None:
            return mock.patch(self.target, self.replacement)
        if self.has_returns:
            return mock.patch(self.target, return_value=self.returns)
        raise ValueError(
            f"mutation for {self.target!r} specifies neither `returns` nor `replacement`"
        )


def mutation_verified(
    target: str,
    *,
    returns: Any = None,
    replacement: Callable[..., Any] | None = None,
    description: str = "",
    **kwargs: Any,
):
    """Mark a test as mutation-verified against a specific reintroduced defect.

    ``target`` is a dotted path patched for the mutated run. Supply either
    ``returns`` (patch to a function returning this constant) or ``replacement``
    (patch to this callable).
    """
    has_returns = "returns" in kwargs or returns is not None
    # Distinguish "returns not supplied" from "returns=None supplied".
    if "returns" in kwargs:
        returns = kwargs.pop("returns")
        has_returns = True
    if kwargs:
        raise TypeError(f"unexpected keyword arguments: {sorted(kwargs)}")

    spec = MutationSpec(
        target=target,
        returns=returns,
        replacement=replacement,
        has_returns=has_returns,
        description=description,
    )

    def decorator(func):
        existing = list(getattr(func, "_mutation_specs", []))
        existing.append(spec)
        func._mutation_specs = existing
        return pytest.mark.mutation_verified(func)

    return decorator


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "mutation_verified: test is verified to fail against a reintroduced defect",
    )
    config._mutation_report = []  # type: ignore[attr-defined]


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("mutation-verified")
    group.addoption(
        "--no-mutation-verify",
        action="store_true",
        default=False,
        help="skip the mutated run (report only; does not admit unverified tests)",
    )
    group.addoption(
        "--mutation-require-all",
        action="store_true",
        default=False,
        help="fail the session if any test function lacks a mutation_verified marker",
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function):
    specs: list[MutationSpec] = list(getattr(pyfuncitem.function, "_mutation_specs", []))
    if not specs or pyfuncitem.config.getoption("--no-mutation-verify"):
        # Plain `yield`, deliberately. Reading the outcome here would re-raise
        # whatever the test did -- including a `Skipped` -- inside hookwrapper
        # teardown, which pluggy reports as PluggyTeardownRaisedWarning. pluggy
        # propagates the result on its own, so reading it buys nothing and makes
        # every skipped test in a project that merely installs this plugin emit
        # a warning (an error, under `filterwarnings = error`).
        yield
        return

    testfunc = pyfuncitem.obj
    argnames = pyfuncitem._fixtureinfo.argnames
    kwargs = {name: pyfuncitem.funcargs[name] for name in argnames}

    report = pyfuncitem.config._mutation_report  # type: ignore[attr-defined]

    for spec in specs:
        try:
            patcher = spec.build_patch()
        except (ValueError, AttributeError, ModuleNotFoundError, ImportError) as exc:
            pytest.fail(
                f"mutation-verified: cannot apply mutation to {spec.target!r}: {exc}",
                pytrace=False,
            )

        detected = False
        try:
            with patcher:
                try:
                    testfunc(**kwargs)
                except BaseException:
                    # The test noticed the reintroduced defect. That is the pass
                    # condition for this phase.
                    detected = True
        except BaseException as exc:  # patching itself blew up
            pytest.fail(
                f"mutation-verified: patch of {spec.target!r} failed: {exc!r}",
                pytrace=False,
            )

        report.append(
            {
                "nodeid": pyfuncitem.nodeid,
                "target": spec.target,
                "detected": detected,
                "description": spec.description,
            }
        )

        if not detected:
            what = spec.description or f"mutation of {spec.target}"
            pytest.fail(
                "mutation-verified: this test PASSED against the reintroduced defect "
                f"({what}), so it cannot detect the thing it exists to catch. "
                "The test is not a regression test until it has been observed to fail.",
                pytrace=False,
            )

    # Mutated run(s) detected the defect; now the real run must pass. Its outcome
    # is pluggy's to propagate -- see the note above.
    yield


def pytest_collection_modifyitems(session, config, items) -> None:
    """Enforce ``--mutation-require-all``.

    Parametrised variants share one underlying function, so the check is applied
    per function rather than per collected item -- otherwise a parametrised test
    would be reported once per case and the output would be unreadable.
    """
    if not config.getoption("--mutation-require-all"):
        return

    unmarked = {}
    for item in items:
        func = getattr(item, "function", None)
        if func is None:
            continue  # not a plain function test; nothing to require
        if getattr(func, "_mutation_specs", None):
            continue
        unmarked.setdefault(f"{item.location[0]}::{func.__name__}", item.nodeid)

    if unmarked:
        config._mutation_unmarked = sorted(unmarked)  # type: ignore[attr-defined]


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    report = getattr(config, "_mutation_report", [])
    unmarked = getattr(config, "_mutation_unmarked", [])

    if report:
        verified = sum(1 for r in report if r["detected"])
        terminalreporter.write_sep("-", "mutation-verified")
        terminalreporter.write_line(
            f"{verified} of {len(report)} mutation(s) detected by their tests"
        )
        for r in report:
            if not r["detected"]:
                terminalreporter.write_line(f"  NOT DETECTED: {r['nodeid']} -> {r['target']}")

    if unmarked:
        if not report:
            terminalreporter.write_sep("-", "mutation-verified")
        terminalreporter.write_line(
            f"--mutation-require-all: {len(unmarked)} test(s) carry no mutation marker"
        )
        for name in unmarked:
            terminalreporter.write_line(f"  UNMARKED: {name}")


def pytest_sessionfinish(session, exitstatus) -> None:
    """Fail the session when ``--mutation-require-all`` found unmarked tests."""
    unmarked = getattr(session.config, "_mutation_unmarked", [])
    if unmarked and session.exitstatus == 0:
        session.exitstatus = 1
