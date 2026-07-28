# Changelog

All notable changes to this package. Format follows [Keep a Changelog](https://keepachangelog.com/);
versioning is [semantic](https://semver.org/).

## [0.1.1]

### Fixed
- **Installing the plugin no longer changes how unrelated tests report.** The hookwrapper read the
  wrapped test's outcome, which re-raised a `Skipped` inside hookwrapper teardown; pluggy reports
  that as `PluggyTeardownRaisedWarning`. Any project that merely had this plugin installed got that
  warning on every skipped test -- and an error, under `filterwarnings = error`. pluggy propagates
  the outcome itself, so the read was never needed. Four regression tests cover it, including that
  an unmarked failure and an unmarked error still surface.

## [0.1.0]
- First release: the `@mutation_verified` decorator, which reintroduces a named defect and asserts
  the test detects it. A test that passes in both the mutated and real states is reported as not
  detecting the defect it claims to catch.
