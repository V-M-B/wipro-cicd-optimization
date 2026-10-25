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
