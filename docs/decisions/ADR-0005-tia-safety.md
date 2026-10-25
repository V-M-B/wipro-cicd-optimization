# ADR-0005: Test impact analysis safety model

**Status:** accepted

## Context
Running fewer tests saves time but risks missing a regression. The dissertation must quantify that risk,
not hide it.

## Decision
- Selection is the union of a conservative static import graph and a dynamic per-test coverage map built by
  the nightly full run. Either alone is known to miss edges (static: reflection/DI; dynamic: code paths not
  exercised during the last run, context caching).
- Hard safety rules force a full suite: CI/workflow changes, build files, lockfiles, Dockerfiles, resources,
  unknown source files, and the codegen templates of the shared library.
- Integration suites that boot the full application run in full on any source change.
- TIA applies only to pull-request and `exp/*` branches. `main` and the nightly run always run everything, so a
  miss is caught within one merge or one night.
- Safety is measured two ways: agreement with the full suite on the replay commits, and recall on a set of
  injected faults (Phase 4).

## Consequences
Savings on backend changes are bounded by the integration suite always running. This is reported, and the
static-only vs hybrid comparison shows how much the dynamic map contributes.

## Addendum (2026-10-25): hub files

The analytics root `conftest.py` imports the whole FastAPI app to build the `TestClient` fixture. Because every
test module implicitly loads `conftest.py`, the static graph made every test depend on every module, and a change
to one metric selected all 33 test files.

Rule added: files matching an app's `hub_globs` remain dependencies of every test (a change to the hub runs the
full suite), but edges *through* a hub are not followed, **only when a fresh dynamic coverage map exists**.
Without the map, hubs are traversed as before. The condition matters: an early version pruned hubs
unconditionally, and a change to `app/api.py` then missed the API tests, which receive the app through the fixture
rather than by import. Import-time breakage behind a hub is still caught, because any selected test loads the hub.
A changed file with no impacted tests at all now falls back to the tests of its mirrored package instead of
selecting nothing.

Measured on single-file changes with the first nightly map (static-only vs hybrid): `metrics/funnel.py` 33 → 5
test files, `api.py` 33 → 8.

## Addendum 2 (2026-10-25): fixture-aware hubs, after a measured miss

The first full fault-injection run (results `tia-faults-20261025T174819Z.json`, analytics) found one miss:
fault `analytics-19` changed a default value in `app/api_models.py`. The only test that detects it calls the API
through the `client` fixture of `tests/conftest.py` and never imports `api_models`. Two mechanisms failed together:
- **Dynamic map:** default values and other module-level code run at import time, during collection, when
  coverage.py has no test context. Import-time lines are attributed to no test.
- **Hub pruning:** with a fresh map, edges through the hub were not followed, so the static path
  `test → conftest → app.api → app.api_models` was cut.

Replacement rule (this addendum supersedes the first addendum's "only with a fresh map" rule): hubs are resolved
per fixture. For each `@pytest.fixture` in the hub, tia computes the modules its body references (through the hub's
module-level imports) plus the fixtures it requests, recursively. Each test module depends on the hub only through
the fixtures it requests (function arguments, `usefixtures` strings) plus autouse fixtures. Helper modules beneath
the hub do not inherit hub edges. A changed hub runs the full suite. A hub that defines pytest hooks is treated as
an ordinary dependency of every test. The rule is the same with or without a coverage map.

Lesson for the dissertation: coverage-based selection is blind to import-time code; static analysis must cover it.
