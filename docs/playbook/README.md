# Portability playbook: CI/CD pipeline optimization on Jenkins, Azure DevOps and GitLab CI

This project measures five optimization techniques on GitHub Actions, using the RetailOps monorepo
(`apps/orders-api` Maven/Java 21, `apps/web` npm/Vite/Vitest/Playwright, `apps/analytics` pip/pytest, one
Docker image per app). Most Wipro client engagements run **Jenkins**, **Azure DevOps** or **GitLab CI**, so
this playbook maps each technique onto those platforms. It also says what to measure, in what order, and what
can go wrong.

| File | Content |
|---|---|
| `README.md` (this file) | The techniques, why they work, their risks, the cross-platform mapping table, and the engagement checklist |
| [`jenkins.md`](jenkins.md) | Declarative pipeline, Kubernetes plugin agents, Job Cacher, `stash`, JUnit plugin, Parallel Test Executor |
| [`azure-devops.md`](azure-devops.md) | `Cache@2`, `dependsOn`, `strategy: parallel`, VMSS agents, container jobs, `PublishTestResults@2` |
| [`gitlab-ci.md`](gitlab-ci.md) | `cache:key:files`, `needs:`, `parallel`/`parallel:matrix`, `rules:changes`, Kubernetes and docker-autoscaler executors |

**About numbers.** This playbook contains no performance figures. The project's measured results come from
`cipro` on real GitHub Actions runs and are written to `docs/phase-results/` (in progress). Where this
playbook says a technique is faster, it explains the mechanism. Whether a technique pays off on a given client
pipeline is something you measure there (see the checklist below).

Reference implementation in this repository (one workflow per stage, ADR-0006):

| Stage | Workflow | Adds |
|---|---|---|
| 0 | `.github/workflows/ci-baseline.yml` | one sequential job, no caches (frozen, ADR-0002) |
| 1 | `.github/workflows/ci-cache.yml` | dependency caches + Docker layer cache |
| 2 | `.github/workflows/ci-parallel.yml` | DAG of parallel jobs + duration-balanced sharding (`shardkit`) |
| 3 | `.github/workflows/ci-optimized.yml` | test impact analysis (`tia`) + per-app image rebuilds |
| 4 | `.github/workflows/ci-ephemeral.yml` | stage 3 on ephemeral autoscaled ARC runners (ADR-0007) |
| — | `.github/workflows/nightly-full.yml` | full suite with per-test coverage, which refreshes the `tia` coverage maps |

---

## 1. The five techniques

### 1.1 Dependency caching and Docker layer caching

**What.** Keep downloaded dependencies (`~/.m2/repository`, the npm download cache, the pip cache, Playwright
browser binaries) and Docker build layers between runs. Each cache key is derived from the file that pins the
dependencies (`pom.xml`, `package-lock.json`, `requirements*.txt`, the Playwright version). The Dockerfiles
(`apps/*/Dockerfile.ci`) copy the dependency manifest and resolve dependencies *before* copying the source,
so a source-only change reuses the dependency layer.

**Why it works.** A cold dependency install makes many network round trips to public registries. Restoring a
cache is one archive download from storage close to the runner. A Docker layer whose inputs are unchanged is
not rebuilt. The win scales with how often the lockfile changes compared with how often code changes.

**Risks.**
- *Stale or poisoned caches.* A key that is too broad, such as a fixed string, restores outdated content. A
  writable cache shared with untrusted branches can be poisoned. Prefer content-hash keys and branch-scoped
  write permissions (all three platforms scope caches in some way; see each platform file).
- *Restore cost greater than rebuild cost.* Restoring a very large cache can take longer than a warm registry
  proxy would. Measure the restore step itself, not only the install step.
- *Hidden non-determinism.* Caching `node_modules` with `npm ci` is pointless (`npm ci` deletes it). Cache the
  npm download cache instead.
- *Docker cache misses from instruction order.* One `COPY . .` before the dependency step invalidates every
  layer after it.

### 1.2 DAG parallelization

**What.** Split the single sequential job into independent jobs (static checks, Java unit tests, Java
integration tests, web unit tests, web build, e2e per browser, analytics tests, image builds) and connect them
only where a real dependency exists (e2e needs the web build; publish needs every test job).

**Why it works.** Wall-clock time falls from the *sum* of the stages to the *longest dependency chain*, the
critical path. `cipro report` computes the critical path heuristically from job timings.

**Risks.**
- *More total compute.* Every job pays its own start-up: provisioning, checkout, toolchain setup, cache
  restore. Billable time can go up even when wall-clock time goes down.
- *Per-job billing granularity.* GitHub rounds each job up to a whole minute (ADR-0004; `cipro` applies this
  rule). Other platforms bill differently: per parallel-job slot on Azure DevOps, compute-minute formula on
  GitLab, your own infrastructure on Jenkins.
- *Concurrency limits.* Fan-out only helps if enough agents or runners are free. Otherwise jobs queue, and
  queue time (which `cipro` reports separately) absorbs the gain.

### 1.3 Duration-balanced sharding (`shardkit`)

**What.** Split a large test suite into N shards with near-equal *duration*, not near-equal *count*.
`shardkit` reads per-test-class or per-file timings from JUnit XML (`shardkit durations`) and assigns units with
longest-processing-time-first greedy bin packing (`shardkit plan --shards N --index i`). The project keeps a
committed snapshot in `experiments/durations/`.

**Why it works.** A sharded job finishes when its slowest shard finishes. Round-robin or alphabetical splits put
several slow integration classes in one shard. Duration balancing minimizes the maximum shard time.
`shardkit compare` reports the imbalance against naive round-robin.

**Risks.**
- *Stale durations.* New or renamed tests have no history. `shardkit` gives them the median, and with no
  history at all it falls back to round-robin. Refresh the durations file from a full run regularly.
- *Fixed per-shard overhead.* Each shard repeats the setup. Beyond some N the setup dominates. Measure the
  wall-clock against billable curve (PLAN.md Phase 3) before picking N.
- *Index conventions differ.* `shardkit --index` is **0-based**. Azure DevOps `System.JobPositionInPhase`,
  GitLab `CI_NODE_INDEX` and Playwright `--shard=x/y` are **1-based**. Subtract 1 where needed.

### 1.4 Test impact analysis (`tia`)

**What.** Run only the tests that a change can affect. `tia select` takes the git diff and returns, per app and
per suite, `none`, `subset` or `full`. It combines a static import graph with the dynamic per-test coverage map
from `nightly-full.yml`, plus the safety rules in `tia.toml` (ADR-0005): CI files, build files, lockfiles,
Dockerfiles and the shared-schema codegen force a full run; Spring Boot integration tests and Playwright e2e run
in full on any source change; with no fresh coverage map, the selection widens to the mirrored test package.

**Why it works.** Most changes touch one app, or one area of an app. Tests that cannot reach the changed code
cannot fail because of it, so skipping them removes their run time and, with per-app image selection, their
image builds as well.

**Risks.**
- *Missed regressions.* Static graphs miss reflection and dependency injection. Dynamic maps miss paths not
  exercised in the last run. The safety net is non-negotiable: **the full suite runs on `main` and nightly**,
  so a miss surfaces within one merge or one night. PLAN.md Phase 4 measures recall with fault injection.
- *Map drift.* A coverage map older than `coverage_max_age_days` is ignored. If the nightly job breaks
  silently, selection quietly becomes static-only and wider.
- *Platform shortcuts are coarser.* Path-based triggers (`rules:changes`, ADO `trigger.paths`, Jenkins
  `when { changeset }`) select whole jobs, not tests. They complement `tia`; they do not replace it.

### 1.5 Ephemeral autoscaled runners

**What.** One fresh agent per job (a Kubernetes pod or a VM), created on demand from a *warm image* with the
toolchains and dependency caches baked in, and destroyed afterwards. The pool scales to zero when idle. The
reference setup is ARC in runner-scale-set mode on k3d (ADR-0007, `infra/`).

**Why it works.** A warm image removes the toolchain and dependency setup from every job. Autoscaling removes
the queue that a fixed agent pool builds up at peak, and avoids paying for idle agents off-peak. One job per
agent removes cross-build contamination.

**Risks.**
- *Cold start.* Pod scheduling, image pull and VM boot add latency. `cipro` reports queue time separately so this
  stays visible.
- *Image staleness.* Baked caches drift from the lockfiles. Rebuild the image on a schedule and keep the normal
  cache step as a fallback.
- *Security.* Docker-in-Docker needs privileged containers (ADR-0007 accepts this only on a single-tenant
  laptop cluster). Never let untrusted fork or merge-request code reach self-hosted agents that hold secrets.
- *Capacity limits.* Cloud quota, subnet size or node capacity cap scale-out. Platform scalers can also be slow;
  Azure's VMSS scaler samples every 5 minutes, for example (see `azure-devops.md`).

---

## 2. Cross-platform mapping

Every platform keyword below is checked in the platform file, which lists the URLs used. Entries marked
"(unverified)" could not be confirmed in official documentation.

| Technique | GitHub Actions (this repo) | Jenkins | Azure DevOps | GitLab CI |
|---|---|---|---|---|
| Dependency cache | `actions/cache@v4`; `setup-java`/`setup-node`/`setup-python` `cache:` | Job Cacher `cache(caches: [arbitraryFileCache(path:, cacheValidityDecidingFile:)])`; PVC workspace; Nexus/Artifactory proxy via Maven `<mirror>` | `Cache@2` with `key: 'maven \| "$(Agent.OS)" \| **/pom.xml'`, `restoreKeys`, `cacheHitVar` | `cache:` with `key: files: [...]`, `paths:`, `policy: pull`, `fallback_keys:`; distributed cache (`[runners.cache] Type = "s3"`) |
| Docker layer cache | `docker/build-push-action@v6` `cache-from/cache-to: type=gha` | `docker buildx build --cache-from/--cache-to type=registry,ref=...` (BuildKit) | same `buildx` registry cache in a script step, or `Cache@2` + `type=local` | `buildx` registry cache in DinD, or rootless BuildKit `--export-cache/--import-cache type=registry` |
| DAG / fan-out | jobs + `needs:` | `parallel { stage ... }` inside a `stage`; scripted `parallel` map | jobs/stages with `dependsOn:` (`dependsOn: []` = no dependency) | `needs:` (up to 50 per job) |
| Matrix | `strategy.matrix` | `matrix { axes { axis { name; values } } }` | `strategy: matrix:` (+ `maxParallel`) | `parallel: matrix:` (≤ 200 jobs) |
| Sharding | matrix over shard index + `shardkit plan --index` | `matrix` axis `SHARD` or scripted `parallel` + `shardkit`; alternative: Parallel Test Executor `splitTests` | `strategy: parallel: N` + `System.JobPositionInPhase` (1-based) / `System.TotalJobsInPhase` + `shardkit` | `parallel: N` + `CI_NODE_INDEX` (1-based) / `CI_NODE_TOTAL` + `shardkit` |
| Test results (durations source) | JUnit XML uploaded with `actions/upload-artifact` | `junit` step (JUnit plugin) | `PublishTestResults@2` (`testResultsFormat: JUnit`) | `artifacts: reports: junit:` |
| Selection / TIA | `select` job → job outputs → `if:` (`scripts/ci_select.py`) | `when { expression { ... } }` on `tia` output; `when { changeset }` (coarse) | output variables + `condition:`; `trigger: paths:` (whole pipeline only); VSTest built-in TIA (.NET Framework only) | `rules: changes:` (+ `compare_to`), or a dynamic child pipeline generated from `tia` |
| Cancel superseded runs | `concurrency: cancel-in-progress` | `options { disableConcurrentBuilds(abortPrevious: true) }` | `trigger: batch: true` batches CI runs (no cancel); YAML pipelines have no queuing policies | `interruptible: true` + `workflow: auto_cancel: on_new_commit:` |
| Job timeout | `timeout-minutes` | `options { timeout(time:, unit:) }` | `timeoutInMinutes` | `timeout:` (job level, not in `default:`) |
| Pass files between jobs | `upload-artifact` / `download-artifact` | `stash` / `unstash` (small files only) | `PublishPipelineArtifact@1` / `DownloadPipelineArtifact@2` | `artifacts:` + `needs:` |
| Ephemeral autoscaled agents | ARC runner scale set (`minRunners: 0`) | Kubernetes plugin: one pod per build, deleted afterwards | VMSS agent pool with "Automatically tear down virtual machines after every use"; Managed DevOps Pools (recommended by Microsoft) | Kubernetes executor (pod per job); docker-autoscaler with `max_use_count = 1` (Docker Machine executor deprecated) |

### Tool portability

| Tool | Input | Platform dependence |
|---|---|---|
| `shardkit` | JUnit XML (surefire/failsafe, Vitest `junit` reporter, Playwright `junit` reporter, pytest `--junitxml`) | None. Runs anywhere Python 3.12 runs; needs only the XML files and `--shards/--index`. |
| `tia` | `git diff` between two commits, `tia.toml`, coverage maps in `experiments/coverage/` | None, but needs **non-shallow history** (or at least the merge base) in the checkout. |
| `cipro` | GitHub REST API (`actions/workflows/{wf}/runs`, `actions/runs/{id}/jobs`, `actions/runs/{id}/timing`, `actions/jobs/{id}/logs`) | **GitHub only today.** Each platform file lists the API endpoints an adapter would need. An adapter would write the same `runs` / `jobs` / `steps` rows (see `tools/cipro/src/cipro/store.py`) so that every metric and `cipro compare` keeps working. |

---

## 3. How to apply this on a Wipro engagement

### 3.1 Profile first

- [ ] Pick one pipeline that runs often (PR validation or the main-branch CI), not the slowest nightly job.
- [ ] Collect at least a few weeks of runs, or a fixed number such as 50, with job-level and step-level start and
      end times. On GitHub use `cipro fetch` + `cipro logs`; on other platforms use the APIs in the platform files.
- [ ] Compute the same metrics `cipro` defines (see `tools/cipro/README.md`):
  - **wall-clock** (first job created to last job completed) and **execution span**,
  - **queue time** (job created to job started), summed and as time-to-first-job,
  - **job-seconds** and **billable minutes** under the platform's real billing rule,
  - **overhead share**: time in runner overhead, checkout, cache, toolchain setup and dependency install ÷ all
    step time,
  - **waste breakdown** by step category (setup/install vs build vs test vs image build vs publish),
  - p50 and p95, not means.
- [ ] Name steps so they can be classified. `cipro` buckets steps by name (`classify.py`), so a step called
      `Run script` is useless. Rename steps on the client pipeline if needed.

### 3.2 Attack the top two waste buckets

- [ ] Rank buckets by share of wall-clock *on the critical path* and by share of billable time.
- [ ] Map each bucket to a technique: install/toolchain → caching or warm images; image build → Docker layer
      cache and Dockerfile ordering; one long test step → DAG and sharding; "every test on every change" →
      TIA; queue time → autoscaled agents or more parallel-job slots.
- [ ] Do the top two first. Stop when the remaining buckets are below the noise between runs.

### 3.3 One change per PR, measured on the same commits

- [ ] Each optimization is its own PR, with a before/after table in the description.
- [ ] Compare **paired runs on the same commits** (run both pipeline variants on each commit, as
      `scripts/replay.py` and `cipro compare` do here). Never compare last week's baseline with this week's
      optimized pipeline. Runner load and code size change in between.
- [ ] Report the median difference with a confidence interval (`cipro compare` uses a paired bootstrap), plus
      billable minutes, not only wall-clock.
- [ ] Warm caches before measuring (caches are branch-scoped on GitHub and Azure DevOps). Report cold-cache
      runs separately.
- [ ] Keep the baseline definition frozen while measuring (ADR-0002).

### 3.4 Governance

- [ ] **Durations file owner.** Name the team or role that owns the `shardkit` durations snapshot and the job
      that refreshes it from a full run (here: committed in `experiments/durations/`, sourced from a baseline
      run). Refresh at least whenever test classes are added or moved.
- [ ] **Coverage map owner.** Name the owner of the nightly job that rebuilds the `tia` coverage maps
      (`nightly-full.yml` → `experiments/coverage/*.json`). Alert on failure: a stale map silently degrades
      selection to static-only.
- [ ] **Cache-key policy.** Keys are content hashes of lockfiles or manifests plus OS and tool version. Add
      `restoreKeys`/`fallback_keys` only for caches where a partial hit is safe (download caches are; build
      outputs often are not).
- [ ] **Cache invalidation.** Write down how to force a miss: a version prefix in the key (Azure DevOps cannot
      clear caches; its documented workaround is changing the key), the GitLab **Clear runner caches** action
      (Build > Pipelines), or changing the `arbitraryFileCache` path/key on Jenkins.
- [ ] **Cache write scope.** Only trusted branches (main, protected branches) write caches that other
      branches read.
- [ ] **TIA safety net.** The full suite always runs on `main` and nightly. TIA runs only on PR and feature
      branches. Safety rules in `tia.toml` are reviewed like code (CODEOWNERS). Every escaped regression gets
      a root cause and, where systematic, a new rule (ADR-0005 addendum is an example).
- [ ] **Self-hosted security.** Ephemeral agents that hold credentials never run fork or untrusted MR/PR code.

### 3.5 When NOT to parallelize

Parallelization moves work from one long job into many short ones. It is a net loss when:

- [ ] **Per-job start-up is a large fraction of each job.** If provisioning, checkout, toolchain setup and
      cache restore take about as long as the work itself, splitting the work into N jobs multiplies the
      overhead by N and saves little wall-clock. ADR-0006 records that this repository's baseline is small in
      absolute terms, which makes these fixed overheads relatively large. That is expected to show in the
      shard-count curve.
- [ ] **Per-job minute rounding dominates.** On GitHub-hosted runners each job is billed in whole minutes, so ten
      40-second jobs bill ten minutes where one 7-minute job bills seven (illustrative arithmetic, not a
      measurement). Check the platform's rule: the GitLab
      compute-minute formula documents no rounding (unverified whether any is applied); Azure DevOps bills
      parallel-job *slots*, so the cost of fan-out there is queueing, not minutes.
- [ ] **There are not enough agents.** With one free Azure DevOps hosted parallel job, or a small static
      Jenkins pool, parallel jobs just queue.
- [ ] **The pipeline is already short.** If p50 is a few minutes and the critical path is one indivisible step
      (such as a single Maven compile), caching and TIA are better first moves.
- [ ] **Shared external resources serialize anyway.** Parallel integration shards that hit the same test
      database or rate-limited sandbox contend with each other.

Rule of thumb: parallelize when the job you are splitting is many times longer than its own start-up
overhead, and measure both wall-clock and billable time on the same commits before keeping the change.
