# CI/CD Pipeline Performance Optimization: Measuring the Impact of Caching, Parallelization, Test Impact Analysis and Ephemeral Runners

*Dissertation draft. (Insert Student Name), (Insert BITS ID). Carried out at Wipro Limited, (Insert Location).*
*Every number in this draft is taken from a file under `docs/phase-results/` or `experiments/results/` in the
project repository and can be regenerated from the archived GitHub API data (README, "Reproduce the numbers").
Placeholders in [brackets] are filled in when replay round B is complete.*

## Abstract

Continuous Integration pipelines in enterprise delivery are often a single sequential job that downloads every
dependency, runs every test and rebuilds every container image on every change. This project measures four common
optimizations on a realistic polyglot workload: dependency and Docker layer caching, parallel jobs with
duration-balanced test sharding, test impact analysis (TIA), and ephemeral autoscaled runners. The workload is a
Java/Spring Boot API, a React/TypeScript web app, a Python/FastAPI service and a shared schema library, with 1,868
automated tests. Each stage was implemented as its own GitHub Actions workflow and run on the same 30 realistic
commits as a frozen baseline, giving paired measurements.

Against a baseline median of 6m 05s, caching reduced median wall-clock by 13.8% and cut the 95th percentile from
27m 04s to 6m 35s, lowering mean cost per 1,000 runs by 42%. Parallelization with test impact analysis reduced median
wall-clock by 62.5%, to 2m 17s, but billed one more minute per run at the median, because many short jobs are each
rounded up to a whole minute. In a 60-fault injection study, test selection caught all 47 faults that the full suites
detect. One unsafe rule was found by the study itself and corrected. The ephemeral-runner stage was built but not
measured, because the author's machine ran out of disk space. The results show that the right optimization depends on
whether a team pays for waiting time or for compute minutes, and that the tail of the build-time distribution, not the
median, drives cost.

## 1. Introduction

**Problem.** Slow pipelines lengthen the feedback loop for developers, encourage large batched changes and consume
shared build capacity whose cost is passed to clients. Optimization advice is plentiful, but it is rarely measured on
one workload, under one method, with its costs as well as its benefits.

**Objectives.**
1. Build a profiler that locates waste in CI pipelines from the provider's API data.
2. Build a representative workload with a frozen, legacy-style baseline.
3. Apply and measure caching, parallelization with sharding, test impact analysis and ephemeral runners, one at a time.
4. Quantify build-time and cost changes with paired measurements and confidence intervals.
5. Evaluate the safety of test impact analysis by fault injection.
6. Produce a portability playbook for Jenkins, Azure DevOps and GitLab CI.

**Contributions.** Three reusable tools: `cipro` (profiler), `shardkit` (sharder) and `tia` (test impact analysis).
A stage-per-workflow experiment design that pairs every stage with the baseline on identical commits. A measured
account of the speed versus cost trade-off. A documented failure and fix of a test-selection rule. A portability
playbook.

## 2. Background and related work

Empirical studies show that CI is widely adopted and valued but costly in build time and developer waiting
(Hilton et al., 2016; Vasilescu et al., 2015). Long build durations have multiple causes, including dependency
resolution and test execution (Ghaleb et al., 2019). Industrial reports from Google (Memon et al., 2017), Facebook
(Machalica et al., 2019) and Microsoft (Herzig et al., 2015) describe running fewer tests with acceptable risk.
Regression test selection has a long academic history, from safe selection (Rothermel and Harrold, 1997) to file-level
dynamic dependencies (Gligoric et al., 2015) and static selection at scale (Legunsen et al., 2016). Yoo and Harman
(2012) survey the area. Mutation-based evaluation (Jia and Harman, 2011) is the standard way to estimate whether a test
subset would have caught a fault. The DevOps literature (Humble and Farley, 2010; Forsgren et al., 2018) links lead
time and deployment frequency to delivery performance, which motivates fast feedback.

## 3. Method

### 3.1 Workload

| App | Stack | Tests |
|---|---|---|
| orders-api | Java 21, Spring Boot 3.5, Maven, PostgreSQL via Testcontainers | 375 unit, 45 integration |
| web | React 18, TypeScript, Vite 7 | 728 Vitest, 35 Playwright × 3 browsers |
| analytics | Python 3.12, FastAPI | 615 pytest |
| shared-schemas | JSON Schema → Java/TS/Python codegen | — |

Generated test tables are a minority (48 Java and 65 web invocations) and use independent reference implementations
for expected values.

### 3.2 Pipelines (one workflow per stage, ADR-0006)

| Stage | Workflow | Adds |
|---|---|---|
| 0 | `ci-baseline.yml` | One sequential job, no caches, everything on every push. Cross-browser e2e and coverage reports included as realistic enterprise stages. Frozen at tag `baseline-v1`. |
| 1 | `ci-cache.yml` | Maven/npm/pip caches, Playwright browser cache, BuildKit `type=gha` layer cache with dependency-first Dockerfiles |
| 2 | `ci-parallel.yml` | Stage 1 + a DAG of parallel jobs + duration-balanced shards (`shardkit`) |
| 3 | `ci-optimized.yml` | Stage 2 + test impact analysis (`tia`) gating every job; full suites on `main` |
| 4 | `ci-ephemeral.yml` | Stage 3 on autoscaled ARC runners with a warm image (built, not measured) |

### 3.3 Experiment design

Thirty commits in six categories (frontend, backend, analytics, shared-lib, docs, config; five each) were authored as
realistic developer changes and verified green. Each round pushes every commit once to a round-specific branch, so the
baseline and the round's stages run on identical inputs. Caches are read from `main`, as for pull requests. Round A
ran the cache and optimized stages, and round B the parallel stage. Rounds keep each commit under the 20
concurrent-job limit of the GitHub Free plan.

### 3.4 Metrics and statistics

Metrics come from the GitHub Actions REST API via `cipro`. **Wall-clock:** first job queued to last job completed.
**Billable minutes:** each job rounded up to a whole minute, GitHub's billing rule. **Cost:** billable minutes × the
list price of $0.006/min for Linux 2-core runners (checked 2026-10-25). Comparisons pair runs by commit and report
the median paired difference with a 95% bootstrap confidence interval (5,000 resamples, fixed seed). Means are reported
for cost, because the bill follows the mean.

### 3.5 Safety evaluation of test impact analysis

Sixty single-site mutations (20 per app, seed 7) were injected into production code. For each fault, the full suite
was run, and the fault was counted as caught by the selection if any failing test unit was in the `tia` selection for
the changed file. Hybrid selection (static graph + nightly coverage map) and static-only selection were both scored.

## 4. Implementation

- **cipro** (standard library only): fetches runs, jobs and steps; archives raw API JSON; parses logs for cache events
  and test counts; computes metrics, a heuristic critical path and paired bootstrap comparisons; renders HTML
  dashboards. 52 tests, 96% coverage.
- **shardkit:** longest-processing-time-first bin packing over per-class or per-file durations from JUnit XML, using
  suite time where class set-up time is otherwise lost. 16 tests, 98% coverage.
- **tia:** static dependency graphs for Java, TypeScript and Python; dynamic per-test coverage maps from JaCoCo,
  Istanbul and coverage.py contexts, built nightly; safety rules (full-suite triggers, integration and e2e suites in
  full on any source change, mirrored-package fallback, fixture-aware handling of pytest `conftest.py` hubs).
  25 tests.

## 5. Results

### 5.1 Baseline profile (10 runs, `phase-0-1-baseline-tables.md`)

Median 6m 13s, p95 39m 03s, mean 14m 30s. Tests take 52.6% of median step time, image builds 18.3% and
dependency/browser installs 18.1%. Three of ten runs took 25–40 minutes, all in the browser and system-package install
step.

### 5.2 Caching (round A, 30 paired commits, `phase-2-results.md`)

| Metric | Baseline | Cache |
|---|---:|---:|
| Wall-clock p50 | 6m 05s | 5m 14s (−13.8%, CI [−62, −38] s) |
| Wall-clock p95 | 27m 04s | 6m 35s |
| Cost per 1,000 runs (mean) | $59.80 | $34.80 |

Docker layer caching is the largest single saving (−44 s at the median). Dependency caches save little on fast hosted
runners, and cache restore and save cost about 12 s. Cache hit rate: 100%.

### 5.3 Parallelization and sharding (round B, `phase-3-results.md`)

[pending: wall-clock and billable minutes vs baseline on 30 paired commits; shard-count curve 1/2/4/8]

### 5.4 Test impact analysis (`phase-4-results.md`, `phase-4-tia-safety.md`)

Against the baseline, median wall-clock fell 62.5%, from 365 s to 137 s (CI [−291, −204] s), while median billable
minutes rose from 7 to 8. Tests executed, as a median share of the baseline's 1,868: docs 0%, backend 5%,
analytics 9%, frontend 11%, config 33%, shared-lib 70%.

**Safety.** All 47 faults that the full suites detect were caught, by both hybrid and static-only selection.
Static-only selection ran 1.3–2.5× more test units. An earlier rule that pruned pytest fixture hubs missed one fault: a
default value in an API model, reached only through a `client` fixture. Coverage attributes import-time code to no test,
and the rule had cut the only static path. The fixture-aware rule fixed it, raising the analytics selection share from
25% to 43%.

### 5.5 Ephemeral runners (`phase-5-results.md`)

Not measured. The runner image and cluster were built and the controller installed, but the author's disk filled
twice, and the phase was stopped on the repository owner's instruction. The infrastructure is ready to run.

## 6. Discussion

**Speed versus cost.** Parallelism buys wall-clock with billed minutes. On GitHub-hosted runners, every job is
rounded up to a whole minute, so splitting a 6-minute job into nine short jobs raised a frontend change's bill from 7
to 12 minutes even with test selection. Teams that pay for developer waiting time should parallelize. Teams that pay
per compute minute should cache first and parallelize only suites long enough to amortize job start-up.

**The tail drives cost.** The cache stage improved the median by 13.8% but cut mean cost by 42%, because it nearly
removed the 25–40-minute runs. Reports that quote only the median understate the value of eliminating external
dependencies from the critical path.

**Selection is the largest lever, and the riskiest.** The safety net (full suites on `main` and nightly), the
always-full suites, and the fault-injection study are what make it acceptable. The miss that was found shows why both
static and dynamic analysis are needed.

**Applicability to Wipro engagements.** The playbook (`docs/playbook/`) maps each technique onto Jenkins, Azure
DevOps and GitLab CI. One finding is that Azure DevOps' built-in TIA supports only .NET Framework VSTest, so a
`tia`-style approach is needed for polyglot estates.

## 7. Threats to validity

- **Workload:** synthetic, though structured like a real estate and small in absolute size (6-minute baseline).
- **Runners:** GitHub-hosted runner variance; paired design and bootstrap CIs mitigate but do not remove it.
- **Tail mechanism:** the slow system-package installs were concentrated in the baseline. The paired runs show the
  effect, but its mechanism was not identified.
- **Replay artefacts:** in round A, commits 2–20 carried an extra one-line file outside every app (a script bug). It
  was verified not to affect any pipeline input. One baseline run was re-run after a transient registry error.
- **Faults:** mutations are single-site and synthetic.
- **Phase 5:** not measured, so the ephemeral-runner question is open.

## 8. Conclusion and future work

Caching is the low-risk first step: it cut median wall-clock by 13.8% and mean cost by 42% on this workload.
Parallelization with test impact analysis cut median wall-clock by 62.5% at a modest cost increase, with selection
safety verified by fault injection. Future work: run Phase 5 on a managed Kubernetes cluster, add a Jenkins and Azure
DevOps adapter to `cipro`, study coverage-map staleness, and evaluate predictive (ML-based) test selection against the
static + dynamic approach.

## References

1. M. Hilton, T. Tunnell, K. Huang, D. Marinov and D. Dig. Usage, costs, and benefits of continuous integration in open-source projects. ASE 2016.
2. T. A. Ghaleb, D. A. da Costa and Y. Zou. An empirical study of the long duration of continuous integration builds. Empirical Software Engineering 24(4), 2019.
3. A. Memon et al. Taming Google-scale continuous testing. ICSE-SEIP 2017.
4. M. Machalica, A. Samylkin, M. Porth and S. Chandra. Predictive test selection. ICSE-SEIP 2019.
5. K. Herzig, M. Greiler, J. Czerwonka and B. Murphy. The art of testing less without sacrificing quality. ICSE 2015.
6. M. Gligoric, L. Eloussi and D. Marinov. Practical regression test selection with dynamic file dependencies. ISSTA 2015.
7. O. Legunsen et al. An extensive study of static regression test selection in modern software evolution. FSE 2016.
8. S. Yoo and M. Harman. Regression testing minimization, selection and prioritization: a survey. STVR 22(2), 2012.
9. G. Rothermel and M. J. Harrold. A safe, efficient regression test selection technique. ACM TOSEM 6(2), 1997.
10. S. Elbaum, G. Rothermel and J. Penix. Techniques for improving regression testing in continuous integration development environments. FSE 2014.
11. B. Vasilescu, Y. Yu, H. Wang, P. Devanbu and V. Filkov. Quality and productivity outcomes relating to continuous integration in GitHub. ESEC/FSE 2015.
12. M. Shahin, M. Ali Babar and L. Zhu. Continuous integration, delivery and deployment: a systematic review. IEEE Access 5, 2017.
13. Y. Jia and M. Harman. An analysis and survey of the development of mutation testing. IEEE TSE 37(5), 2011.
14. J. Humble and D. Farley. Continuous Delivery. Addison-Wesley, 2010.
15. N. Forsgren, J. Humble and G. Kim. Accelerate. IT Revolution, 2018.
16. GitHub Docs: Actions runner pricing; Actions Runner Controller. Accessed 25 October 2026.

## Appendices

A. Decision records ADR-0001 to ADR-0007 (`docs/decisions/`). B. Replay patches and manifest (`experiments/commits/`).
C. Injected faults (`experiments/faults/`). D. Per-run tables (`docs/phase-results/round-a-tables.md`).
E. Figures (`docs/dissertation/figures/`).
