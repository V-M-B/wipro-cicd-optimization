# GitLab CI playbook

How to apply the five techniques (see [README](README.md)) in `.gitlab-ci.yml`, for the RetailOps monorepo in
this repository. The snippets adapt `.github/workflows/ci-*.yml`; this project has not run them on GitLab. No
timings are claimed here. The project's measured numbers are in `docs/phase-results/` (in progress).

Conventions used below:

```yaml
stages: [select, test, build, publish]

variables:
  TIA: env PYTHONPATH=tools/tia/src python3 -m tia.cli
  SHARDKIT: env PYTHONPATH=tools/shardkit/src python3 -m shardkit.cli
  GIT_DEPTH: "0"                         # full history: tia needs the merge base (new projects default to 20)

default:
  image: $CI_REGISTRY_IMAGE/ci-warm:latest   # warm image built like infra/runner-image (placeholder)
  interruptible: true                        # safe to cancel when a newer commit arrives

workflow:
  auto_cancel:
    on_new_commit: interruptible             # = concurrency: cancel-in-progress
```

Billing context: GitLab compute minutes are documented as `job duration / 60 × cost factor`, where duration
excludes time in `created`/`pending`. The page does not mention rounding per job (unverified whether any is
applied), unlike GitHub's whole-minute rounding (ADR-0004). Fan-out still repeats per-job start-up, which the
runner pays in setup time even if the bill does not round.

---

## 1. Dependency caching: `cache:` with `key:files`

**Mechanism.** `cache:key:files` hashes the listed files (up to 10) into the key; `key:prefix` namespaces it.
`policy` is `pull-push` (default), `pull` or `push`, and the docs recommend `pull` for parallel jobs that only
read. `fallback_keys` lists keys to try when the main key misses. A job can use at most **four caches**. Cache
paths must be **inside the project directory**, so point each tool's cache there:

```yaml
variables:
  MAVEN_OPTS: "-Dmaven.repo.local=$CI_PROJECT_DIR/.m2/repository"
  npm_config_cache: "$CI_PROJECT_DIR/.npm"
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
  PLAYWRIGHT_BROWSERS_PATH: "$CI_PROJECT_DIR/.cache/ms-playwright"

.cache-maven: &cache-maven
  key: { prefix: maven, files: [apps/orders-api/pom.xml] }
  paths: [.m2/repository]
  policy: pull

.cache-npm: &cache-npm
  key: { prefix: npm, files: [apps/web/package-lock.json] }
  paths: [.npm, .cache/ms-playwright]        # the lockfile pins the Playwright version too
  policy: pull

.cache-pip: &cache-pip
  key: { prefix: pip, files: [apps/analytics/requirements.txt, apps/analytics/requirements-dev.txt] }
  paths: [.cache/pip]
  policy: pull

# One job per cache refreshes it on the default branch; every other job only pulls.
warm-caches:
  stage: select
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  cache:
    - { <<: *cache-maven, policy: pull-push }
    - { <<: *cache-npm, policy: pull-push }
    - { <<: *cache-pip, policy: pull-push }
  script:
    - (cd apps/orders-api && ./mvnw -B -q dependency:go-offline)
    - (cd apps/web && npm ci && npx playwright install chromium firefox webkit)
    - pip download -d /tmp/wheels -r apps/analytics/requirements-dev.txt   # fills PIP_CACHE_DIR
```

**Caveats.**
- **Protected vs unprotected.** By default keys get a `-protected` or `-non_protected` suffix, so feature
  branches do not read caches written by protected branches unless that setting is turned off. GitLab calls
  it a security feature: keep it on unless every Developer is fully trusted. Under the default, warm
  non-protected caches separately or accept cold feature-branch runs.
- **Where caches live.** By default on the runner machine (Docker volumes for the Docker executor). Autoscaled
  and Kubernetes runners start on fresh machines, so configure a **distributed cache** (section 6) or every
  job is cold.
- Caching is best effort ("isn't guaranteed to always work"). Jobs must still succeed on a miss.
- To invalidate: **Build > Pipelines > Clear runner caches** (Developer role or higher; the next commit uses a
  new cache), or change `cache:key`.
- Use **artifacts**, not cache, for build outputs another job *needs* (such as the Vite `dist/`).

---

## 2. Docker layer caching

**Option A: Docker-in-Docker with a BuildKit registry cache** (GitLab's documented pattern). Since Docker
27.0.1 the default `docker` driver supports cache backends only with the containerd image store, so create a
`docker-container` builder:

```yaml
.image-build:
  stage: build
  image: docker:27.4.1-cli
  services: [docker:27.4.1-dind]
  variables:
    DOCKER_HOST: tcp://docker:2376
    DOCKER_TLS_CERTDIR: "/certs"
  before_script:
    - echo "$CI_REGISTRY_PASSWORD" | docker login -u "$CI_REGISTRY_USER" --password-stdin "$CI_REGISTRY"
    - docker context create builder-ctx
    - docker buildx create builder-ctx --driver docker-container --use
  script:
    - >
      docker buildx build --push
      -f apps/$APP/Dockerfile.ci
      -t $CI_REGISTRY_IMAGE/$APP:$CI_COMMIT_SHA
      --cache-from type=registry,ref=$CI_REGISTRY_IMAGE/$APP/cache
      --cache-to type=registry,ref=$CI_REGISTRY_IMAGE/$APP/cache,mode=max
      apps/$APP

images:
  extends: .image-build
  parallel:
    matrix:
      - APP: [orders-api, web, analytics]
```

**Option B: rootless BuildKit** (no daemon, no privileged container; GitLab presents it as a Kaniko
replacement). Use `moby/buildkit:rootless` with `entrypoint: [""]` (otherwise the job starts the daemon and
hangs), `BUILDKITD_FLAGS: --oci-worker-no-process-sandbox`, a `~/.docker/config.json` written from the
`CI_REGISTRY*` variables, and `buildctl-daemonless.sh build ... --export-cache type=registry,ref=$CACHE_IMAGE
--import-cache type=registry,ref=$CACHE_IMAGE`.

**Caveats.** DinD needs `privileged = true` on the runner (Docker or Kubernetes executor), which is the security
trade-off ADR-0007 documents. `mode=max` caches all intermediate layers, so the cache image grows; that is
what makes the dependency stage of the multi-stage `Dockerfile.ci` reusable. Pin client and service to the
same Docker version.

---

## 3. DAG parallelization: `needs:`

**Mechanism.** `needs:` starts a job as soon as the listed jobs finish, regardless of stage order (up to 50 jobs
per `needs`; `needs: []` starts immediately). `needs:artifacts: false` skips downloading their artifacts, and
`optional: true` tolerates a needed job that `rules` removed from the pipeline.

```yaml
orders-unit:
  stage: test
  needs: [select]
  timeout: 20m
  cache: [*cache-maven]
  script:
    - units=$($TIA show --selection selection.json --app orders-api --suite unit --style maven)   # artifact of select
    - '[ -n "$units" ] || { echo "tia: no unit tests selected"; exit 0; }'
    - cd apps/orders-api && ./mvnw -B verify -DskipITs -Dsurefire.failIfNoSpecifiedTests=false -Dtest="$units"
  artifacts:
    when: always
    reports: { junit: apps/orders-api/target/surefire-reports/TEST-*.xml }

web-build:
  stage: test
  needs: []
  cache: [*cache-npm]
  script: [cd apps/web && npm ci && npm run build]
  artifacts: { paths: [apps/web/dist], expire_in: 3 days }

web-e2e:
  stage: test
  needs: [web-build, select]                  # gets dist/ from web-build and selection.json from select
  cache: [*cache-npm]
  parallel:
    matrix:
      - BROWSER: [chromium, firefox, webkit]
  script:
    - specs=$($TIA show --selection selection.json --app web --suite e2e --style args)
    - '[ -n "$specs" ] || { echo "tia: no e2e specs selected"; exit 0; }'
    - cd apps/web && npm ci && npx playwright test --project=$BROWSER $specs
  artifacts:
    when: always
    reports: { junit: apps/web/reports/e2e-junit.xml }

publish:
  stage: publish
  needs: [orders-unit, orders-it, web-unit, web-e2e, analytics, images]
  rules:
    - if: $CI_PIPELINE_SOURCE != "merge_request_event"
  script: [echo "retag and push from the registry cache (section 2)"]
```

`timeout:` must be set per job (it is not supported under `default:`), and a job cannot exceed the runner's
own timeout.

---

## 4. Sharding: `parallel:` with `CI_NODE_INDEX` / `CI_NODE_TOTAL`

**Mechanism.** `parallel: N` (1 to 200) creates jobs named `name 1/N` … `name N/N`, each with `CI_NODE_INDEX`
and `CI_NODE_TOTAL`. The naming implies a **1-based** index (the docs do not state the base explicitly), and
`shardkit --index` is 0-based:

```yaml
orders-it:
  stage: test
  needs: [select]
  timeout: 30m
  parallel: 2
  cache: [*cache-maven]
  services: [docker:27.4.1-dind]               # Testcontainers needs a Docker daemon (privileged runner;
  variables: { DOCKER_HOST: tcp://docker:2376, DOCKER_TLS_CERTDIR: "/certs" }   # extra Testcontainers settings unverified)
  script:
    - $TIA show --selection selection.json --app orders-api --suite integration --style lines > units.txt
    - '[ -s units.txt ] && grep -q . units.txt || { echo "tia: no integration tests selected"; exit 0; }'
    - >
      classes=$($SHARDKIT plan --framework junit --durations experiments/durations/orders-it.json
      --units-file units.txt --shards $CI_NODE_TOTAL --index $((CI_NODE_INDEX - 1)) --style maven --summary)
    - '[ -z "$classes" ] || (cd apps/orders-api && ./mvnw -B verify -Dtest=NoUnitTestsInThisShard -Dsurefire.failIfNoSpecifiedTests=false -Dit.test=$classes)'
  artifacts:
    when: always
    reports: { junit: apps/orders-api/target/failsafe-reports/TEST-*.xml }
```

Playwright can shard natively with `--shard=$CI_NODE_INDEX/$CI_NODE_TOTAL` (both 1-based). `parallel:matrix`
(at most 200 permutations) is for named variants such as browsers, not for duration-balanced shards.

**Caveats.**
- `parallel: N` is static. A selection that shrinks to two test files still starts N jobs, which then exit
  early. To size the fan-out to the selection, use a dynamic child pipeline (section 5).
- GitLab also documents a **Test balancing API** that hands out duration-budgeted batches to `parallel:` jobs.
  It is an **Experiment** (GitLab 19.4, Ultimate, behind the `parallel_test_balancing` feature flag, "not ready
  for production use"). `shardkit` is the portable choice until it is generally available.

---

## 5. Test impact analysis: `tia` (and where `rules:changes` fits)

**`rules:changes` is a job-level path filter**, finer than Azure DevOps triggers but still coarse: it includes or
excludes a whole job. Use `compare_to` so feature branches compare against `main`. Without it, on a new branch
or a pipeline with no push event, `changes` "always evaluates to true":

```yaml
.web-paths: &web-paths
  - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH            # safety net: main runs everything
  - changes:
      compare_to: refs/heads/main
      paths: [apps/web/**/*, libs/shared-schemas/**/*, tia.toml, .gitlab-ci.yml, tools/**/*]
```

Keep these globs at least as wide as `tia.toml`'s `always_full_globs` and the app's `full_globs`, or a CI or
schema change could skip a suite that `tia` would have run in full.

**`tia` for test-level selection.** `rules` are evaluated when the pipeline is created, so they cannot read
another job's output. Two working patterns:

*Pattern A: a `select` job plus early exit (simple).* `select` publishes `selection.json` as an artifact. Jobs
that `needs: [select]` download it, call `tia show` for their suite and exit 0 when the list is empty (as in
sections 3 and 4). Do not pass the test lists through `artifacts:reports:dotenv`: dotenv files are limited to
5 KB with no multiline values, and a full selection is longer than that. Dotenv suits small values such as
the per-app `mode`, and like any job output, dotenv variables cannot be used in `rules`.

```yaml
select:
  stage: select
  needs: []
  timeout: 5m
  script:
    - |
      if [ "$CI_COMMIT_BRANCH" = "$CI_DEFAULT_BRANCH" ]; then
        $TIA select --config tia.toml --force-full "main branch safety net" --out selection.json
      else
        # the runner may fetch only the pipeline's own ref (default refspecs unverified), so fetch main explicitly
        git fetch --no-tags origin "+refs/heads/$CI_DEFAULT_BRANCH:refs/remotes/origin/$CI_DEFAULT_BRANCH"
        base="${CI_MERGE_REQUEST_DIFF_BASE_SHA:-$(git merge-base origin/$CI_DEFAULT_BRANCH HEAD)}"
        $TIA select --config tia.toml --base "$base" --head HEAD --out selection.json
      fi
    - |
      for app in orders-api web analytics; do
        echo "MODE_${app//-/_}=$($TIA show --selection selection.json --app $app --field mode)"
      done > selection.env                     # small values only: none | subset | full
  artifacts:
    paths: [selection.json]
    reports: { dotenv: selection.env }
```

The cost of pattern A is that skipped suites still start a job, pull the image and restore caches before
exiting.

*Pattern B: a dynamic child pipeline (sized to the selection).* The `select` job writes a pipeline file that
contains only the impacted jobs, with `parallel:` set from the number of selected units (as
`scripts/ci_select.py` computes `<suite>_shards`). The generator is not part of this repository.

```yaml
run-selected:
  stage: test
  needs: [select]
  trigger:
    include:
      - artifact: child-pipeline.yml
        job: select
    strategy: mirror        # the trigger job's status mirrors the child pipeline
```

Limits: no CI/CD variables in the child `include`, at most two levels of nesting, and child pipelines run as
branch pipelines (`$CI_PIPELINE_SOURCE` is `parent_pipeline` inside them).

**Safety net.** A scheduled pipeline (pipeline schedule on `main`) runs everything with `--force-full` and
rebuilds `experiments/coverage/*.json`, like `.github/workflows/nightly-full.yml`. `CI_COMMIT_BEFORE_SHA` is all
zeros for merge request, scheduled and first-push pipelines, so never use it as the `tia` base.

---

## 6. Ephemeral autoscaled runners

**Kubernetes executor.** Creates "a pod for each GitLab CI job": a build container, a helper container (clone,
cache and artifact transfer) and one container per `services:` entry. Leftover pods can remain if the runner
manager shuts down badly; the docs point to a pod-cleanup application.

```toml
concurrent = 6

[[runners]]
  name = "retailops-k8s"
  url = "https://gitlab.example.com"
  executor = "kubernetes"
  [runners.kubernetes]
    namespace = "gitlab-ci"
    cpu_request = "2"
    memory_request = "3Gi"
    privileged = true          # only if DinD/Testcontainers is needed; prefer rootless BuildKit for images
  [runners.cache]
    Type = "s3"                # s3 | gcs | azure
    Shared = true              # share the cache between runners
```

**docker-autoscaler executor** (replaces the deprecated Docker Machine executor, which GitLab deprecated in 17.5
and schedules for removal in 20.0). It uses fleeting plugins (`aws`, `googlecloud`, `azure`) over an AWS Auto
Scaling group, a GCP instance group or an Azure scale set. `capacity_per_instance = 1` with `max_use_count = 1`
gives "a secure ephemeral instance" per job, deleted afterwards:

```toml
[[runners]]
  executor = "docker-autoscaler"
  [runners.docker]
    image = "registry.example.com/retailops/ci-warm:latest"
  [runners.autoscaler]
    plugin = "aws"
    capacity_per_instance = 1
    max_use_count = 1
    max_instances = 10
    [[runners.autoscaler.policy]]
      idle_count = 0           # scale to zero; raise during working hours to hide cold start
      idle_time = "20m0s"
```

The plugin-specific blocks (instance group name, connector settings) follow the docs' per-cloud examples and are
not reproduced here (unverified for your cloud). Install the plugin with `gitlab-runner fleeting install`.

**Caveats.** With one job per instance, cold start (VM boot, image pull) lands in the job's queue time. GitLab's
`queued_duration` field captures it (section 8). Bake toolchains and dependencies into the instance or container
image, as `infra/runner-image/` does for ARC. Protected runners and protected variables keep untrusted MR code
away from credentials.

---

## 7. Test results and `shardkit` durations: `artifacts:reports:junit`

`artifacts:reports:junit` accepts a file, a glob such as `test-results/**/*.xml`, or a list (no directories).
Reports are uploaded even when the job fails, show in the MR **Test summary** and the pipeline **Tests** tab, and
must be under 30 MB per file and 100 MB per job. Add `artifacts:paths` too if you need the raw XML downloadable
(the file is then stored twice). RetailOps report paths are listed in `jenkins.md` §5.

Feeding `shardkit` from the scheduled full run:

```yaml
durations:
  stage: publish
  needs: [orders-it, web-unit, analytics]       # full-suite jobs in the scheduled pipeline
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
  script:
    - $SHARDKIT durations --framework junit --junit 'apps/orders-api/target/failsafe-reports/*.xml' --out out/orders-it.json
    - $SHARDKIT durations --framework pytest --junit 'apps/analytics/reports/*.xml' --root apps/analytics --out out/analytics.json
  artifacts:
    paths: [out/]
```

This works only if the upstream jobs also keep the XML in `artifacts:paths`. An owner reviews and commits the
result to `experiments/durations/` (README §3.4). The pipeline test report API
(`GET /projects/:id/pipelines/:pipeline_id/test_report`) is an alternative source of per-test durations.

---

## 8. Profiling with `cipro`

**Current state.** `cipro fetch`/`cipro logs` call only the GitHub REST API. There is no GitLab adapter in this
repository. Metrics, reports and `cipro compare` read the `runs`/`jobs`/`steps` tables in
`tools/cipro/src/cipro/store.py`. GitLab's API maps onto them closely:

| cipro table | GitLab REST API v4 (`$CI_API_V4_URL`) | Fields |
|---|---|---|
| `runs` | `GET /projects/:id/pipelines?ref=...&sha=...&source=...&updated_after=...`, then `GET /projects/:id/pipelines/:pipeline_id` | `id`, `sha` (pairing key), `ref`, `source`, `status`, `created_at`, `started_at`, `finished_at`, `duration`, `queued_duration` (the list response shows only some timestamps, so fetch each pipeline) |
| `jobs` | `GET /projects/:id/pipelines/:pipeline_id/jobs` (20 per page by default; `include_retried=true` for retries) | `name`, `stage`, `status`, `created_at`, `started_at`, `finished_at`, `duration`, `queued_duration`, `runner` (`description`, `is_shared`, `runner_type`) |
| `steps` | no step-level timing endpoint: parse the job log | `GET /projects/:id/jobs/:job_id/trace`; step timings would come from the log's collapsible section markers (format unverified) |
| tests | `GET /projects/:id/pipelines/:pipeline_id/test_report` (and `/test_report_summary`) | per-suite and per-case results and durations |

What the adapter must decide:
- **Queue time** is native (`queued_duration` per job), which is better than Jenkins or Azure DevOps.
- **Billable minutes.** Use GitLab's formula (`duration / 60 × cost factor` per runner type) in `pricing.toml`,
  with the cost factors' source and date. Do not apply GitHub's per-job round-up.
- **Step classification.** Without step records, the waste breakdown needs named log sections. Wrap each logical
  step in a named section in the job script, and keep names aligned with `classify.py`.
- **Auth.** A project access token or personal access token with read API scope outside CI. `CI_JOB_TOKEN` works
  only for certain endpoints while the job runs.

---

## References

All accessed 2026-10-25.

- CI/CD YAML syntax reference (`cache`, `needs`, `parallel`, `parallel:matrix`, `rules:changes`, `compare_to`, `artifacts`, `interruptible`, `timeout`, `workflow:auto_cancel`, `default`): https://docs.gitlab.com/ci/yaml/
- Caching in GitLab CI/CD (protected-branch separation, storage, clearing, best effort): https://docs.gitlab.com/ci/caching/
- Specify when jobs run with rules (`rules:changes` with `compare_to`): https://docs.gitlab.com/ci/jobs/job_rules/
- Control how jobs run (parallel matrix jobs, matrix variables in `rules:changes`): https://docs.gitlab.com/ci/jobs/job_control/
- Predefined CI/CD variables (`CI_NODE_INDEX`, `CI_NODE_TOTAL`, `CI_COMMIT_BEFORE_SHA`, `CI_MERGE_REQUEST_DIFF_BASE_SHA`, `CI_DEFAULT_BRANCH`, `CI_REGISTRY*`, `CI_API_V4_URL`): https://docs.gitlab.com/ci/variables/predefined_variables/
- Unit test reports (`artifacts:reports:junit`, limits): https://docs.gitlab.com/ci/testing/unit_test_reports/
- Test balancing API (Experiment): https://docs.gitlab.com/api/test_balancing/
- Downstream pipelines (dynamic child pipelines, `strategy: mirror`): https://docs.gitlab.com/ci/pipelines/downstream_pipelines/
- Pass dotenv variables to specific jobs (`artifacts:reports:dotenv`, 5 KB limit, not usable in `rules`): https://docs.gitlab.com/ci/variables/dotenv_variables/
- Cache Docker layers in Docker-in-Docker builds: https://docs.gitlab.com/ci/docker/docker_layer_caching/
- Build Docker images with BuildKit (rootless, registry cache): https://docs.gitlab.com/ci/docker/using_buildkit/
- Use Docker to build Docker images (DinD, alternatives to privileged mode): https://docs.gitlab.com/ci/docker/using_docker_build/
- Kubernetes executor: https://docs.gitlab.com/runner/executors/kubernetes/
- Docker Autoscaler executor: https://docs.gitlab.com/runner/executors/docker_autoscaler/
- Docker Machine executor (deprecation): https://docs.gitlab.com/runner/executors/docker_machine/
- Advanced runner configuration (`[runners.cache]` `Type`, `Shared`): https://docs.gitlab.com/runner/configuration/advanced-configuration/
- Compute minutes (formula, cost factor): https://docs.gitlab.com/ci/pipelines/compute_minutes/
- Customize pipeline configuration (shallow clone depth, default 20): https://docs.gitlab.com/ci/pipelines/settings/
- Pipelines API: https://docs.gitlab.com/api/pipelines/
- Jobs API (pipeline jobs, `queued_duration`, trace): https://docs.gitlab.com/api/jobs/
- Playwright, Sharding: https://playwright.dev/docs/test-sharding
- Playwright, Browsers (`PLAYWRIGHT_BROWSERS_PATH`): https://playwright.dev/docs/browsers
