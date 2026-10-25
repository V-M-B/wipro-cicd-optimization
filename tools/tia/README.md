# tia — test impact analysis

Selects which tests to run for a change, per app and per suite, and explains why.

**How it decides (per app):**

1. A change matching a global trigger (`always_full_globs`, e.g. CI files) runs everything.
2. Only ignored files changed (docs) or nothing in the app changed: run nothing.
3. A change matching the app's `full_globs` (build files, lockfiles, Dockerfile, resources) runs the full suite.
4. Otherwise, union of:
   - **static** impact: tests whose transitive import closure contains a changed file
     (Java imports + same-package references, TypeScript relative/alias imports and `vi.mock`, Python imports
     including package `__init__` and `conftest.py`);
   - **dynamic** impact: tests that executed a changed file in the last full coverage run (`coverage_map`),
     only if the map is younger than `coverage_max_age_days`;
   - changed test files themselves, and configured smoke tests.
5. Without a fresh coverage map, selection is **widened** to tests in the mirrored package/folder of each changed
   source file (catches DI wiring and reflection that import analysis cannot see).
6. Suites listed in `full_suite_on_source_change` (e.g. Spring Boot integration tests that boot the whole
   context) run in full on any source change. Per-test coverage is unreliable for them because Spring caches
   the application context across test classes, so startup code is attributed to only one class.
7. A changed source file that appears in no graph and has an extension in `unknown_file_full_exts` forces the
   full suite (new files, or files the analyzer could not parse).

`main` and the nightly run always execute the full suite; that is the safety net (see ADR-0005).

```bash
pip install -e tools/tia[dev]
tia select --config tia.toml --base origin/main --head HEAD --out selection.json
tia show --selection selection.json --app orders-api --suite unit --style maven   # comma-separated classes
tia show --selection selection.json --app web --field mode                         # none | subset | full
tia coverage-python --coverage-json coverage.json --prefix apps/analytics --out experiments/coverage/analytics.json
tia coverage-merge a.json b.json --out merged.json
```

Configuration reference: docstring at the top of `src/tia/select.py`; real config in `/tia.toml`.

Tests: `cd tools/tia && pytest --cov=tia` (16 tests, 98% coverage).
