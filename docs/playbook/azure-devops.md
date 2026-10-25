# Azure DevOps playbook

How to apply the five techniques (see [README](README.md)) in **Azure Pipelines YAML**, for the RetailOps
monorepo in this repository. The snippets adapt `.github/workflows/ci-*.yml`; this project has not run them on
Azure DevOps. No timings are claimed here. The project's measured numbers are in `docs/phase-results/` (in
progress).

Conventions used below:

```yaml
pool:
  vmImage: ubuntu-latest

variables:
  TIA: env PYTHONPATH=tools/tia/src python3 -m tia.cli
  SHARDKIT: env PYTHONPATH=tools/shardkit/src python3 -m shardkit.cli
  REGISTRY: retailops.azurecr.io            # placeholder
```

Billing context that changes the trade-offs: Microsoft-hosted capacity is bought as **parallel jobs** (slots),
not per minute. The free tier is one job of up to 60 minutes with a 1,800 minutes/month limit for private
projects; paid hosted jobs run up to 360 minutes. Public projects are retired and convert to private in 2027. So
on Azure DevOps, fan-out costs **queueing** when slots run out, and `cipro`'s per-minute cost model does not
apply as-is (section 7).

---

## 1. Dependency caching: `Cache@2`

**Mechanism.** `Cache@2` takes `key` (segments separated by `|`; a segment that looks like a file path or a glob
is hashed), optional `restoreKeys` (prefix fallbacks, most recent entry wins), `path` (no wildcards) and
`cacheHitVar` (`true`, `inexact` or `false`). A post-job step saves the cache after all steps succeeded.

```yaml
variables:
  MAVEN_CACHE_FOLDER: $(Pipeline.Workspace)/.m2/repository
  npm_config_cache: $(Pipeline.Workspace)/.npm
  PIP_CACHE_DIR: $(Pipeline.Workspace)/.pip
  PLAYWRIGHT_BROWSERS_PATH: $(Pipeline.Workspace)/ms-playwright

steps:
- task: Cache@2
  displayName: Cache Maven local repo
  inputs:
    key: 'maven | "$(Agent.OS)" | apps/orders-api/pom.xml'
    restoreKeys: |
      maven | "$(Agent.OS)"
    path: $(MAVEN_CACHE_FOLDER)
- script: ./mvnw -B -Dmaven.repo.local=$(MAVEN_CACHE_FOLDER) verify -DskipITs
  workingDirectory: apps/orders-api
  displayName: orders-api - unit tests

- task: Cache@2
  displayName: Cache npm
  inputs:
    key: 'npm | "$(Agent.OS)" | apps/web/package-lock.json'
    restoreKeys: |
      npm | "$(Agent.OS)"
    path: $(npm_config_cache)

- task: Cache@2
  displayName: Cache pip
  inputs:
    key: 'pip | "$(Agent.OS)" | apps/analytics/requirements-dev.txt, apps/analytics/requirements.txt'
    restoreKeys: |
      pip | "$(Agent.OS)"
    path: $(PIP_CACHE_DIR)

- task: Cache@2
  displayName: Cache Playwright browsers
  inputs:
    key: 'playwright | "$(Agent.OS)" | apps/web/package-lock.json'   # lockfile pins the Playwright version
    path: $(PLAYWRIGHT_BROWSERS_PATH)
    cacheHitVar: PW_CACHE_RESTORED
- script: npx playwright install --with-deps chromium firefox webkit
  workingDirectory: apps/web
  condition: ne(variables.PW_CACHE_RESTORED, 'true')
- script: npx playwright install-deps chromium firefox webkit
  workingDirectory: apps/web
  condition: eq(variables.PW_CACHE_RESTORED, 'true')
```

**Caveats.**
- **Caches are immutable.** A key, once saved in a scope, is never updated. A fixed key freezes the cache, so
  always hash the lockfile. There is no "clear cache": the documented workaround is adding a literal such as
  `version2 |` to the key.
- **Scope.** Caches are isolated per pipeline and branch. CI runs read their own branch and `main`/`master`
  and write only their own branch. PR runs read the source, target and `main` scopes, but write only to the
  merge scope (`refs/pull/N/merge`). Warm `main` first, as this project does for `exp/*` branches (ADR-0006).
- Caches expire after **seven days without activity**. Monday-morning runs after a quiet week can be cold.
- Do not cache `node_modules` with `npm ci` (it deletes the folder); cache `npm_config_cache` as above.
- Self-hosted agents need GNU tar (Linux/Windows) or BSD tar (macOS), and 7-Zip is recommended on Windows.
- The Maven task overwrites `MAVEN_OPTS`. Pass `$(MAVEN_OPTS)` in its `mavenOptions`, or use a script step
  with `-Dmaven.repo.local` as above.
- The comma-separated file list in the pip key follows the documented "file patterns" segment form; a combined
  key over two files is not shown verbatim in the docs (unverified). Hashing only `requirements-dev.txt` is the
  conservative fallback if it includes `requirements.txt`.

---

## 2. Docker layer caching

**Mechanism.** Azure Pipelines has no BuildKit cache backend of its own. Two documented options:

1. **Registry cache** with `docker buildx` in a script step. `Docker@2` handles the registry login, but its
   `buildAndPush` command **ignores `arguments`**, so it cannot pass `--cache-from/--cache-to`:

```yaml
- task: Docker@2
  displayName: Log in to registry
  inputs:
    command: login
    containerRegistry: retailops-acr          # Docker registry service connection
- script: |
    docker buildx create --name ci --driver docker-container --use
    docker buildx build --push \
      -f apps/$(app)/Dockerfile.ci \
      -t $(REGISTRY)/retailops-$(app):$(Build.SourceVersion) \
      --cache-from type=registry,ref=$(REGISTRY)/retailops-$(app):buildcache \
      --cache-to type=registry,ref=$(REGISTRY)/retailops-$(app):buildcache,mode=max \
      apps/$(app)
  displayName: Build and push $(app) with registry cache
```

2. **`Cache@2` + BuildKit local cache** (`--cache-from=type=local,src=...` / `--cache-to=type=local,dest=...,mode=max`
   on a `docker-container` builder). This is Microsoft's own buildx example. It stays inside the pipeline's
   cache scope, but every run uploads and downloads the whole cache directory.

The `docker-container` driver is required because the default `docker` driver supports cache backends only
with the containerd image store. The dependency-first `apps/*/Dockerfile.ci` is what makes either cache useful.

---

## 3. DAG: jobs with `dependsOn`, and output variables

**Mechanism.** Jobs in a stage run **in parallel by default** unless `dependsOn` says otherwise. Stages run in
sequence unless `dependsOn: []`. A stage can hold up to 256 jobs. Multi-job output variables
(`##vso[task.setvariable variable=X;isOutput=true]`, read as `dependencies.JOB.outputs['STEP.X']`) work only for
jobs **in the same stage**, so keep the whole CI DAG in one stage.

```yaml
trigger:
  branches: { include: [main, exp/*] }

jobs:
- job: select
  timeoutInMinutes: 5
  steps:
  - checkout: self
    fetchDepth: 0                               # tia needs the merge base; new pipelines may default to depth 1
  - bash: |
      set -euo pipefail
      if [ "$(Build.SourceBranch)" = "refs/heads/main" ]; then
        $(TIA) select --config tia.toml --force-full "main branch safety net" --out selection.json
      else
        target="$(System.PullRequest.TargetBranch)"      # empty outside PR builds
        target="${target#refs/heads/}"; target="${target:-main}"
        $(TIA) select --config tia.toml --base "$(git merge-base origin/$target HEAD)" --head HEAD --out selection.json
      fi
      out() { echo "##vso[task.setvariable variable=$1;isOutput=true]$($(TIA) show --selection selection.json --app $2 --suite $3 --style $4)"; }
      out ordersUnit orders-api unit maven
      out ordersIt   orders-api integration maven
      out webUnit    web unit args
      out webE2e     web e2e args
      out analytics  analytics unit args
    name: tia
  - task: PublishPipelineArtifact@1
    inputs: { targetPath: selection.json, artifactName: tia-selection }

- job: orders_unit
  dependsOn: select
  condition: and(succeeded(), ne(dependencies.select.outputs['tia.ordersUnit'], ''))
  timeoutInMinutes: 20
  variables:
    units: $[ dependencies.select.outputs['tia.ordersUnit'] ]
  steps:
  - script: ./mvnw -B verify -DskipITs -Dsurefire.failIfNoSpecifiedTests=false -Dtest=$(units)
    workingDirectory: apps/orders-api
    displayName: orders-api - selected unit tests

- job: web_build
  dependsOn: select
  steps:
  - script: npm ci && npm run build
    workingDirectory: apps/web
  - task: PublishPipelineArtifact@1
    inputs: { targetPath: apps/web/dist, artifactName: web-dist }

- job: web_e2e
  dependsOn: [select, web_build]
  condition: and(succeeded(), ne(dependencies.select.outputs['tia.webE2e'], ''))
  strategy:
    matrix:
      chromium: { browser: chromium }
      firefox:  { browser: firefox }
      webkit:   { browser: webkit }
  steps:
  - task: DownloadPipelineArtifact@2
    inputs: { artifactName: web-dist, targetPath: apps/web/dist }
  - script: npm ci && npx playwright test --project=$(browser)
    workingDirectory: apps/web

- job: publish
  dependsOn: [orders_unit, orders_it, web_unit, web_e2e, analytics, images]
  condition: and(not(failed()), not(canceled()), ne(variables['Build.Reason'], 'PullRequest'))
  steps:
  - script: echo "push images from the registry cache (section 2)"
```

The default job condition needs every dependency to have "completed and succeeded", so a test job that `tia`
skipped would also skip `publish`. The custom condition above is meant to mirror the
`!contains(needs.*.result, 'failure')` guard in `ci-optimized.yml`. How `failed()` treats a *skipped*
dependency is not spelled out in the conditions page (unverified). The explicit alternative is checking each
`dependencies.<job>.result` (the docs show this form with `'SucceededWithIssues'`; the literal `'Skipped'` is
unverified).

**Caveats.**
- `trigger.paths` include/exclude filters decide whether the **whole pipeline** runs. They cannot skip
  individual jobs and are evaluated on the pushed changes, so they are a coarse complement to `tia`, not a
  replacement. Variables cannot be used in path filters.
- YAML pipelines have no queuing policies and no `cancel-in-progress` equivalent. `trigger: batch: true` waits
  for the running build and then builds all pending changes together. That saves capacity but breaks the
  one-run-per-commit pairing that `cipro compare` relies on, so do not enable it on experiment branches.
- Each job gets a fresh Microsoft-hosted agent. Every job repeats checkout, toolchain setup and cache restore.
- A full selection puts every test class or file into one output variable. A size limit for output variables
  was not found in the docs (unverified). If it bites, have each job download the `tia-selection` artifact and
  run `tia show` itself, and keep only the per-app `mode` in output variables.

---

## 4. Sharding: `strategy: parallel` and `System.JobPositionInPhase`

**Mechanism.** `strategy: parallel: N` duplicates a job N times and sets `System.JobPositionInPhase` and
`System.TotalJobsInPhase` in each copy (up to 99 agents). Microsoft's sample scripts treat the position as
**1-based** (they index `$tests[$i-1]`). `shardkit --index` is 0-based, so subtract 1:

```yaml
- job: web_unit
  dependsOn: select
  condition: and(succeeded(), ne(dependencies.select.outputs['tia.webUnit'], ''))
  timeoutInMinutes: 15
  strategy:
    parallel: 2
  variables:
    units: $[ dependencies.select.outputs['tia.webUnit'] ]
  steps:
  - script: npm ci
    workingDirectory: apps/web
  - bash: |
      set -euo pipefail
      echo "$(units)" > units.txt
      idx=$(( $(System.JobPositionInPhase) - 1 ))
      files=$($(SHARDKIT) plan --framework vitest --durations experiments/durations/web-unit.json \
        --units-file units.txt --shards $(System.TotalJobsInPhase) --index $idx --style args --summary)
      if [ -n "$files" ]; then (cd apps/web && npx vitest run --coverage $files); fi
    displayName: web - unit tests (slice $(System.JobPositionInPhase)/$(System.TotalJobsInPhase))
```

**Shard count sized to the selection.** `parallel` is fixed when the run is planned, but `matrix` accepts a
runtime expression that expands to a JSON object from an output variable. That lets the `select` job size the
fan-out the way `scripts/ci_select.py` does (`<suite>_shards`):

```yaml
# in the select job's bash step, e.g. for two integration-test shards:
#   echo "##vso[task.setvariable variable=itLegs;isOutput=true]{'s0':{'SHARD':'0'},'s1':{'SHARD':'1'}}"
- job: orders_it
  dependsOn: select
  condition: and(succeeded(), ne(dependencies.select.outputs['tia.ordersIt'], ''))
  strategy:
    matrix: $[ dependencies.select.outputs['tia.itLegs'] ]
  variables:
    units: $[ dependencies.select.outputs['tia.ordersIt'] ]
  steps:
  - bash: |
      echo "$(units)" > units.txt
      classes=$($(SHARDKIT) plan --framework junit --durations experiments/durations/orders-it.json \
        --units-file units.txt --shards 2 --index $(SHARD) --style maven)
      cd apps/orders-api && ./mvnw -B verify -Dtest=NoUnitTestsInThisShard \
        -Dsurefire.failIfNoSpecifiedTests=false -Dit.test=$classes
```

Keep the `--shards` value consistent with the number of legs the `select` job emitted (or emit it as a second
matrix variable, for example `{'s0':{'SHARD':'0','TOTAL':'2'}, ...}`).

**Caveats.** Each slice consumes a parallel-job slot. With the free tier's single hosted job, slices run one
after another and add only overhead. The Visual Studio Test task slices tests natively, but only for VSTest
(.NET) suites. Matrix leg names must be letters, digits and underscores, and must start with a letter.

---

## 5. Test impact analysis

**Built-in TIA does not apply to RetailOps.** Azure Pipelines' Test Impact Analysis runs through the Visual
Studio Test task (`VSTest@2`, "Run only impacted tests"). It is scoped to **managed code** on a **single
machine**, and it is documented as **not supported for .NET Core**, data-driven tests or multi-machine
topologies. It falls back to all tests for files it cannot reason about. Custom dependency maps
(`TIA.UserMapFile`) still feed VSTest selection only. For Java, TypeScript and Python suites, use `tia` as in
section 3. Two of Microsoft's TIA recommendations carry over directly:
- run all tests periodically (here: the full suite on `main` and the nightly schedule), and
- validate selection by running the selected set and then the full set and comparing failures (this
  project's agreement study, PLAN.md Phase 4).

Nightly safety-net run (a separate pipeline). Cron schedules are in UTC. Without `always: true` a schedule only
runs if the code changed since the last *successful* scheduled run, which would let the coverage map age past
`coverage_max_age_days` over a quiet weekend:

```yaml
trigger: none
pr: none
schedules:
- cron: '41 1 * * *'
  displayName: nightly full suite + coverage maps
  branches:
    include: [main]
  always: true
```

The nightly jobs run the same commands as `.github/workflows/nightly-full.yml` and publish
`experiments/coverage/*.json` as a pipeline artifact for the owner to commit.

**Caveats.** New pipelines may default to a shallow fetch of depth 1. Set `fetchDepth: 0` (or a depth that
reliably contains the merge base) in the `select` job. `System.PullRequest.TargetBranch` is `refs/heads/main` for
Azure Repos but `main` for GitHub repositories, and in YAML it is only set when a branch policy triggered
the PR build. The snippet in section 3 strips the prefix and defaults to `main`.

---

## 6. Test results and `shardkit` durations: `PublishTestResults@2`

```yaml
- task: PublishTestResults@2
  condition: succeededOrFailed()
  inputs:
    testResultsFormat: JUnit
    testResultsFiles: |
      apps/orders-api/target/surefire-reports/TEST-*.xml
      apps/orders-api/target/failsafe-reports/TEST-*.xml
      apps/web/reports/*.xml
      apps/analytics/reports/*.xml
    mergeTestResults: true
    failTaskOnMissingResultsFile: false    # TIA subsets and empty shards may produce nothing
    testRunTitle: retailops
```

`mergeTestResults: true` reports one test run per job and helps durations come out right for files from the
same framework (results are merged anyway above 100 files). Microsoft's JUnit mapping reads per-test duration
from `testcase@time`, the same attribute `shardkit durations` uses.

Feeding `shardkit`: the Tests tab is for people. For `shardkit`, publish the raw XML from the nightly full run
as a pipeline artifact and convert it:

```yaml
- bash: |
    $(SHARDKIT) durations --framework junit --junit 'apps/orders-api/target/failsafe-reports/*.xml' --out out/orders-it.json
    $(SHARDKIT) durations --framework vitest --junit 'apps/web/reports/junit.xml' --strip-prefix apps/web --out out/web-unit.json
  condition: succeeded()                   # never derive durations from a failed or partial run
- task: PublishPipelineArtifact@1
  inputs: { targetPath: out, artifactName: shardkit-durations }
```

---

## 7. Ephemeral and autoscaled agents

**VM scale set agents.** A self-hosted pool backed by an Azure VMSS that Azure Pipelines scales itself (VMSS
autoscaling and overprovisioning must be disabled). Pool settings that matter here:
- **Automatically tear down virtual machines after every use**: the VM is reimaged before its next job (one job
  per clean machine, like ARC's ephemeral runners). Supported for Windows Server and supported Linux images,
  not Windows client images.
- **Maximum number of virtual machines**, and **Number of agents to keep on standby**: `0` means a VM starts
  only when a job is waiting (scale to zero).
- **Delay in minutes before deleting excess idle agents**: default behavior scales in after 30 minutes of
  excess idle agents.
- Bake toolchains, Playwright browsers and pre-fetched dependencies into the **custom image**: this is the
  warm-image equivalent of `infra/runner-image/`. A Custom Script Extension can warm caches at boot.

Scaling is slow by design. The pool is sampled **every 5 minutes**, scale-out happens in steps ("allow 20
minutes for machines to be created for each step"), and Microsoft notes that scaling can take an hour or more.
Expect a cold pool to show up as queue time. Measure it, and size standby agents for peak hours.
Microsoft now recommends **Managed DevOps Pools**, an evolution of VMSS agent pools, for new autoscaled pools.

**Container jobs** give a clean, versioned toolchain per job without managing VMs:

```yaml
resources:
  containers:
  - container: warm
    image: retailops.azurecr.io/ci-warm:latest     # placeholder; built like infra/runner-image
    endpoint: retailops-acr

jobs:
- job: analytics
  container: warm
  steps:
  - script: pytest --junitxml=reports/junit.xml
    workingDirectory: apps/analytics
```

Requirements: YAML pipelines, Ubuntu or Windows agents (no macOS), Docker on the agent, the agent running
directly on the host (no nested containers), and for Linux images bash, glibc, no `ENTRYPOINT`, and the
ability to run the agent's Node.js. Since agent 5.279.0, Linux container jobs **do not mount the host Docker
socket** unless the container resource sets `mapDockerSocket: true`, which gives the job root-equivalent
access to the host. Build images in a non-container job (section 2) rather than opting in.

---

## 8. Profiling with `cipro`

**Current state.** `cipro fetch`/`cipro logs` call only the GitHub REST API. There is no Azure DevOps adapter in
this repository. Metrics, reports and `cipro compare` read the `runs`, `jobs` and `steps` SQLite tables
(`tools/cipro/src/cipro/store.py`), so an adapter needs to fill those and archive the raw responses (ADR-0004).

| cipro table | Azure DevOps REST API (7.1) | Fields |
|---|---|---|
| `runs` | `GET https://dev.azure.com/{org}/{project}/_apis/build/builds?definitions={id}&branchName=...&minTime=...&$top=...` (page with `continuationToken`) | `id`, `queueTime`, `startTime`, `finishTime`, `sourceVersion` (pairing key), `sourceBranch`, `result`, `reason` |
| `jobs`, `steps` | `GET .../_apis/build/builds/{buildId}/timeline` | `records[]`: `type`, `name`, `startTime`, `finishTime`, `parentId`, `result`, `state`, `workerName`, `queueId`, `attempt`, `log` |
| logs (`cipro logs`) | log referenced by each record's `log.url` | parse cache hit/miss (`Cache@2` prints the restored key) and test counts |

What the adapter must decide:
- **Record types.** The docs list `type` as a string without enumerating values. Stage, phase, job and task
  records are distinguished by it; the exact strings are unverified. Build the job→step tree from `parentId`.
- **Queue time.** The build has `queueTime` and `startTime`, so build-level time-to-first-job is available.
  Per-job queue time is not an explicit timeline field (unverified). Approximate it as job `startTime` minus the
  `finishTime` of the jobs it depends on, and say so.
- **Cost.** There are no billable minutes: hosted capacity is a fixed number of parallel-job slots per month.
  Report job-seconds and queue time. Model cost as slots × slot price, or self-hosted VM time × a cited price
  in `pricing.toml` (source URL and date).
- **Auth.** Inside a pipeline use `System.AccessToken` (map it explicitly via `env:`). Outside, use a PAT with
  the `vso.build` scope.
- **Step names.** `cipro` classifies steps by name. Give every step a `displayName` that matches the buckets in
  `classify.py` (for example `orders-api - install`, `web - unit tests`).

---

## References

All accessed 2026-10-25.

- Pipeline caching (`Cache@2`, keys, scopes, immutability, expiry, Docker/buildx examples): https://learn.microsoft.com/en-us/azure/devops/pipelines/release/caching?view=azure-devops
- Jobs (dependencies, conditions, timeouts, matrix from output variables, slicing): https://learn.microsoft.com/en-us/azure/devops/pipelines/process/phases?view=azure-devops
- Stages (`dependsOn`, `dependsOn: []`, 256 jobs per stage, no YAML queuing policies): https://learn.microsoft.com/en-us/azure/devops/pipelines/process/stages?view=azure-devops
- `jobs.job.strategy` (matrix, maxParallel, parallel): https://learn.microsoft.com/en-us/azure/devops/pipelines/yaml-schema/jobs-job-strategy?view=azure-pipelines
- Run any tests in parallel (`System.JobPositionInPhase`, `System.TotalJobsInPhase`, 99 agents): https://learn.microsoft.com/en-us/azure/devops/pipelines/test/parallel-testing-any-test-runner?view=azure-devops
- Microsoft sample `DistributeTests.ps1` (1-based slice position): https://raw.githubusercontent.com/PBoraMSFT/ParallelTestingSample-Python/master/DistributeTests.ps1
- Define variables (multi-job output variables, `isOutput=true`, `dependencies`/`stageDependencies`): https://learn.microsoft.com/en-us/azure/devops/pipelines/process/variables?view=azure-devops
- Predefined variables (`Build.SourceBranch`, `Build.SourceVersion`, `System.PullRequest.TargetBranch`, `System.AccessToken`, `Pipeline.Workspace`, `Agent.OS`): https://learn.microsoft.com/en-us/azure/devops/pipelines/build/variables?view=azure-devops
- `steps.checkout` (`fetchDepth`, shallow fetch default): https://learn.microsoft.com/en-us/azure/devops/pipelines/yaml-schema/steps-checkout?view=azure-pipelines
- Azure Repos Git triggers (path filters, `batch`): https://learn.microsoft.com/en-us/azure/devops/pipelines/repos/azure-repos-git?view=azure-devops
- Use Test Impact Analysis (VSTest, managed code, not .NET Core): https://learn.microsoft.com/en-us/azure/devops/pipelines/test/test-impact-analysis?view=azure-devops
- `PublishTestResults@2`: https://learn.microsoft.com/en-us/azure/devops/pipelines/tasks/reference/publish-test-results-v2?view=azure-pipelines
- `Docker@2` (`buildAndPush` ignores `arguments`): https://learn.microsoft.com/en-us/azure/devops/pipelines/tasks/reference/docker-v2?view=azure-pipelines
- Azure Virtual Machine Scale Set agents: https://learn.microsoft.com/en-us/azure/devops/pipelines/agents/scale-set-agents?view=azure-devops
- Container jobs (requirements, `mapDockerSocket`): https://learn.microsoft.com/en-us/azure/devops/pipelines/process/container-phases?view=azure-devops
- Configure and pay for parallel jobs: https://learn.microsoft.com/en-us/azure/devops/pipelines/licensing/concurrent-jobs?view=azure-devops
- Pipeline conditions (`succeeded()`, `succeededOrFailed()`, `failed()`, `dependencies.<job>.result`): https://learn.microsoft.com/en-us/azure/devops/pipelines/process/conditions?view=azure-devops
- Scheduled triggers (`schedules`, `always`, UTC): https://learn.microsoft.com/en-us/azure/devops/pipelines/process/scheduled-triggers?view=azure-devops
- REST API Builds - List (7.1): https://learn.microsoft.com/en-us/rest/api/azure/devops/build/builds/list?view=azure-devops-rest-7.1
- REST API Timeline - Get (7.1): https://learn.microsoft.com/en-us/rest/api/azure/devops/build/timeline/get?view=azure-devops-rest-7.1
- Docker, Registry cache backend: https://docs.docker.com/build/cache/backends/registry/
- Playwright, Browsers (`PLAYWRIGHT_BROWSERS_PATH`): https://playwright.dev/docs/browsers
