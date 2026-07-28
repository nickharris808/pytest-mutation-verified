# Changelog

All notable changes to this package. Format follows [Keep a Changelog](https://keepachangelog.com/);
versioning is [semantic](https://semver.org/).

## [0.1.0]
- First release: the `@mutation_verified` decorator, which reintroduces a named defect and asserts
  the test detects it. A test that passes in both the mutated and real states is reported as not
  detecting the defect it claims to catch.
