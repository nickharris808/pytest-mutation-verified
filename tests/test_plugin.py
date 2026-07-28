"""Tests for the plugin.

These use pytest's own ``pytester`` fixture, which runs a real pytest session in
a temp directory. That is the only honest way to test a plugin: assert on what an
actual run reports, not on the plugin's internals.
"""

import pytest

pytest_plugins = ["pytester"]

# NOTE: these runs deliberately do NOT pass `-p pytest_mutation_verified.plugin`.
# The package registers itself as a pytest11 entry point, so an installed copy
# loads automatically -- and passing `-p` as well makes pluggy raise
# "Plugin already registered under a different name". Testing without the flag
# is also the honest configuration: it is what a real user gets from pip.


def test_a_real_regression_test_is_admitted(pytester: pytest.Pytester):
    """The good case: the test detects the reintroduced defect, then passes."""
    pytester.makepyfile(
        """
        from pytest_mutation_verified import mutation_verified
        from pytest_mutation_verified.example_pkg import read

        @mutation_verified(
            target="pytest_mutation_verified.example_pkg.check_bounds",
            returns=True,
            description="bounds check always passes",
        )
        def test_oversized_read_is_refused():
            assert read(b"abc", 0, 99) is None
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*1 of 1 mutation(s) detected*"])


def test_a_test_that_cannot_fail_is_rejected(pytester: pytest.Pytester):
    """The whole point: a test that passes against the defect is refused."""
    pytester.makepyfile(
        """
        from pytest_mutation_verified import mutation_verified
        from pytest_mutation_verified.example_pkg import read

        @mutation_verified(
            target="pytest_mutation_verified.example_pkg.check_bounds",
            returns=True,
        )
        def test_asserts_something_unrelated():
            # This assertion is true whether or not the bounds check works, so
            # the test cannot detect the defect it claims to catch.
            assert isinstance(read(b"abc", 0, 2), (bytes, type(None)))
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*PASSED against the reintroduced defect*"])


def test_unverified_test_reported_in_summary(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        from pytest_mutation_verified import mutation_verified
        from pytest_mutation_verified.example_pkg import read

        @mutation_verified(
            target="pytest_mutation_verified.example_pkg.check_bounds",
            returns=True,
        )
        def test_weak():
            assert True
        """
    )
    result = pytester.runpytest()
    result.stdout.fnmatch_lines(["*NOT DETECTED:*"])


def test_replacement_callable_form(pytester: pytest.Pytester):
    """`replacement=` patches to a callable rather than a constant."""
    pytester.makepyfile(
        """
        from pytest_mutation_verified import mutation_verified
        from pytest_mutation_verified.example_pkg import read

        @mutation_verified(
            target="pytest_mutation_verified.example_pkg.check_bounds",
            replacement=lambda o, l, c: True,
            description="off-by-one: capacity check removed",
        )
        def test_detects_it():
            assert read(b"abc", 0, 99) is None
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_untagged_tests_are_untouched(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        def test_ordinary():
            assert 1 + 1 == 2
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_no_mutation_verify_flag_skips_the_mutated_run(pytester: pytest.Pytester):
    """The escape hatch must not silently admit an unverifiable test as verified."""
    pytester.makepyfile(
        """
        from pytest_mutation_verified import mutation_verified

        @mutation_verified(
            target="pytest_mutation_verified.example_pkg.check_bounds",
            returns=True,
        )
        def test_weak():
            assert True
        """
    )
    result = pytester.runpytest("--no-mutation-verify")
    result.assert_outcomes(passed=1)
    # With the flag set there is no report at all -- nothing is claimed.
    assert "mutation(s) detected" not in result.stdout.str()


def test_bad_target_fails_loudly(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        from pytest_mutation_verified import mutation_verified

        @mutation_verified(target="no.such.module.attr", returns=True)
        def test_x():
            assert True
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)


def test_mutation_without_returns_or_replacement_is_an_error(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        from pytest_mutation_verified import mutation_verified

        @mutation_verified(target="pytest_mutation_verified.example_pkg.check_bounds")
        def test_x():
            assert True
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*neither*returns*replacement*"])


def test_fixtures_are_passed_through(pytester: pytest.Pytester):
    """The mutated run must receive the same fixtures as the real run."""
    pytester.makepyfile(
        """
        import pytest
        from pytest_mutation_verified import mutation_verified
        from pytest_mutation_verified.example_pkg import read

        @pytest.fixture
        def buf():
            return b"abc"

        @mutation_verified(
            target="pytest_mutation_verified.example_pkg.check_bounds",
            returns=True,
        )
        def test_with_fixture(buf):
            assert read(buf, 0, 99) is None
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_multiple_mutations_all_must_be_detected(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        from pytest_mutation_verified import mutation_verified
        from pytest_mutation_verified.example_pkg import read

        @mutation_verified(
            target="pytest_mutation_verified.example_pkg.check_bounds",
            returns=True,
        )
        @mutation_verified(
            target="pytest_mutation_verified.example_pkg.check_bounds",
            replacement=lambda o, l, c: True,
        )
        def test_two():
            assert read(b"abc", 0, 99) is None
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*2 of 2 mutation(s) detected*"])


def test_example_package_behaves_as_documented():
    """The README's worked example must actually be true."""
    from pytest_mutation_verified.example_pkg import check_bounds, read

    assert read(b"abcdef", 1, 3) == b"bcd"
    assert read(b"abc", 0, 99) is None
    assert check_bounds(0, 3, 3) is True
    assert check_bounds(1, 3, 3) is False


def test_require_all_fails_when_a_test_is_unmarked(pytester: pytest.Pytester):
    """--mutation-require-all must actually enforce, not merely parse."""
    pytester.makepyfile(
        """
        def test_unmarked():
            assert True
        """
    )
    result = pytester.runpytest("--mutation-require-all")
    assert result.ret != 0, "session should fail when a test carries no marker"
    result.stdout.fnmatch_lines(["*UNMARKED:*"])


def test_require_all_passes_when_every_test_is_marked(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        from pytest_mutation_verified import mutation_verified
        from pytest_mutation_verified.example_pkg import read

        @mutation_verified(
            target="pytest_mutation_verified.example_pkg.check_bounds",
            returns=True,
        )
        def test_marked():
            assert read(b"abc", 0, 99) is None
        """
    )
    result = pytester.runpytest("--mutation-require-all")
    assert result.ret == 0
    result.assert_outcomes(passed=1)


def test_require_all_is_off_by_default(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        def test_unmarked():
            assert True
        """
    )
    result = pytester.runpytest()
    assert result.ret == 0
    result.assert_outcomes(passed=1)


def test_require_all_counts_a_parametrised_test_once(pytester: pytest.Pytester):
    """Per-function, not per-case, or the report is unreadable."""
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
        def test_unmarked(n):
            assert n
        """
    )
    result = pytester.runpytest("--mutation-require-all")
    assert result.ret != 0
    result.stdout.fnmatch_lines(["*1 test(s) carry no mutation marker*"])
