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
