# Jenkins playbook

How to apply the five techniques (see [README](README.md)) on Jenkins, using a **Multibranch Pipeline** with a
declarative `Jenkinsfile` and these plugins: Kubernetes, Job Cacher, JUnit, Pipeline: Basic Steps (`stash`),
Pipeline: Stage View (REST API used for profiling) and, optionally, Parallel Test Executor. The examples target
the RetailOps monorepo in this repository. They are adaptations of the GitHub Actions workflows in
`.github/workflows/`, not something this project has run on Jenkins. No timings are claimed here. The project's
measured numbers are in `docs/phase-results/` (in progress).

Conventions used below:

```groovy
// Top of the Jenkinsfile: tools from this repo, run straight from source (no install needed).
environment {
  TIA      = 'env PYTHONPATH=tools/tia/src python3 -m tia.cli'
  SHARDKIT = 'env PYTHONPATH=tools/shardkit/src python3 -m shardkit.cli'
}
```

---

## 1. Ephemeral agents: Kubernetes plugin pod templates

**Mechanism.** The Kubernetes plugin "creates a Kubernetes Pod for each agent started, and stops it after each
build". The agent process runs in the `jnlp` container; other containers in the pod hold the toolchains, and
`container('name')` (or `defaultContainer`) chooses where steps run. Do not set `idleMinutes` (it keeps pods
alive for reuse); leaving it unset gives one clean pod per build, which is the equivalent of ARC's ephemeral
runners (ADR-0007).

Pod template kept in the repo (`ci/jenkins/pod.yaml`, path illustrative). The `build` image is a **warm image**
built like `infra/runner-image/Dockerfile` (JDK 21, Node 20, Python 3.12, Playwright browsers, pre-fetched
Maven/npm/pip dependencies), minus the GitHub runner:

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: build
    image: registry.example.com/retailops/ci-warm:latest   # placeholder; rebuild weekly
    command: ["sleep"]
    args: ["infinity"]
    resources:
      requests: { cpu: "2", memory: 3Gi }
  - name: buildkit                     # rootless BuildKit for image builds, no Docker daemon
    image: moby/buildkit:rootless
    command: ["sleep"]
    args: ["infinity"]
    env:
    - name: BUILDKITD_FLAGS
      value: --oci-worker-no-process-sandbox
```

Declarative use:

```groovy
agent { kubernetes { yamlFile 'ci/jenkins/pod.yaml'; defaultContainer 'build' } }
```

Scripted use (needed for dynamic fan-out, section 3), via the generated `POD_LABEL`:

```groovy
def inPod(Closure body) {
  podTemplate(yaml: env.POD_YAML) {          // POD_YAML is read once in the Select stage
    node(POD_LABEL) { container('build') { checkout scm; body() } }
  }
}
```

**Caveats.**
- Rootless BuildKit needs relaxed seccomp/AppArmor settings on most clusters. Follow BuildKit's
  `docs/rootless.md` for the exact `securityContext` (not reproduced here, unverified for your cluster). The
  alternative is a privileged `docker:dind` sidecar, with the same trade-off ADR-0007 documents.
- Mounting the node's `/var/run/docker.sock` (shown in the plugin docs as a `hostPathVolume` example) gives
  builds root on the node. Avoid it on shared clusters.
- Restrict which branches and PRs may use the pod cloud. Never build untrusted fork PRs on agents that can
  read registry or deploy credentials.
- Cold start (pod scheduling and image pull) shows up as time before the first step runs. Pre-pull the warm
  image on nodes, or use a node image cache.

---

## 2. Caching

### 2.1 Dependencies: Job Cacher plugin

**Mechanism.** The `cache` step restores caches "before calling the closure and updated after executing it".
Storage is on the controller by default; S3-compatible, Azure, GCS, Artifactory and ORAS backends come from
extension plugins. The plugin targets ephemeral executors. With container agents, **the cached path must be
inside the workspace**, so point each tool's cache there:

```groovy
environment {
  npm_config_cache = "${WORKSPACE}/.npm"         // npm download cache inside the workspace
  PIP_CACHE_DIR    = "${WORKSPACE}/.pip-cache"   // pip download cache inside the workspace
}                                                // Maven: pass -Dmaven.repo.local explicitly (below)
// ...
cache(maxCacheSize: 4096, defaultBranch: 'main', caches: [
  arbitraryFileCache(path: '.m2/repository', cacheValidityDecidingFile: 'apps/orders-api/pom.xml'),
  arbitraryFileCache(path: '.npm',           cacheValidityDecidingFile: 'apps/web/package-lock.json'),
  arbitraryFileCache(path: '.pip-cache',     cacheValidityDecidingFile: 'apps/analytics/requirements-dev.txt',
                     compressionMethod: 'TAR_ZSTD'),
]) {
  sh 'cd apps/orders-api && ./mvnw -B -Dmaven.repo.local=$WORKSPACE/.m2/repository verify -DskipITs'
}
```

**Caveats.** `maxCacheSize` is a ceiling: when it is exceeded the plugin deletes *all* caches, so the next build
is cold. Its unit (MB) and the exact fallback semantics of `defaultBranch` are taken from the plugin's option
table and example (unverified in detail). Controller-side storage puts cache traffic on the controller. Use an
object-store backend for many parallel pods.

### 2.2 Dependencies: repository manager (Nexus / Artifactory)

Usually the best first move on Jenkins estates, because most Wipro clients already run one. Point Maven at a
proxying repository with a mirror in a CI `settings.xml` (`mirrorOf` `*` "is most useful with an internal
repository manager"):

```xml
<settings>
  <mirrors>
    <mirror>
      <id>retailops-proxy</id>
      <url>https://nexus.example.com/repository/maven-public/</url>
      <mirrorOf>*</mirrorOf>
    </mirror>
  </mirrors>
</settings>
```

```groovy
sh 'cd apps/orders-api && ./mvnw -B -s ../../ci/maven-settings.xml verify -DskipITs'
```

npm (`registry=` in `.npmrc`) and pip (`index-url` in `pip.conf`) proxies work the same way. A proxy removes the
internet round trips but still downloads every artifact into each fresh pod. Combine it with Job Cacher or the
warm image when install time is still a top waste bucket.

### 2.3 Persistent volume workspace

`persistentVolumeClaimWorkspaceVolume()` mounts an existing PVC as the workspace (the default is
`emptyDirWorkspaceVolume`). This keeps `~/.m2` between builds without archive and restore, but concurrent pods
writing the same volume need a ReadWriteMany volume and tolerate Maven/npm's lack of cross-process locking
poorly (unverified for your storage class). Prefer it for a single serialized job (for example the nightly run).

### 2.4 Docker layers: BuildKit registry cache

The equivalent of `cache-from/cache-to type=gha` is BuildKit's **registry** cache exporter. In the `buildkit`
container (daemonless mode, one ephemeral daemon per command):

```groovy
container('buildkit') {
  sh '''
    buildctl-daemonless.sh build \
      --frontend dockerfile.v0 \
      --local context=apps/orders-api --local dockerfile=apps/orders-api \
      --opt filename=Dockerfile.ci \
      --output type=image,name=${REGISTRY}/retailops-orders-api:${GIT_COMMIT},push=false \
      --export-cache type=registry,ref=${REGISTRY}/retailops-orders-api:buildcache,mode=max \
      --import-cache type=registry,ref=${REGISTRY}/retailops-orders-api:buildcache
  '''
}
```

On agents with a Docker daemon the same thing is
`docker buildx build --cache-to type=registry,ref=...,mode=max --cache-from type=registry,ref=...`, which needs a
`docker-container` builder (or the containerd image store) because the default `docker` driver does not support
cache backends otherwise. The dependency-first `apps/*/Dockerfile.ci` files are what make the cache effective.
Registry credentials go into `~/.docker/config.json` from a Jenkins credential (Credentials Binding plugin).

---

## 3. DAG parallelization and sharding

### 3.1 Declarative `parallel` (static fan-out)

Declarative stages run in order. Fan-out is a `parallel` block inside one stage, and fan-in is the next stage.
Nested `parallel` or `matrix` inside a parallel branch's `stage` is not allowed, but a branch may contain
sequential `stages`, which is how "e2e after web build" is expressed. When the consumer runs in a *different*
pod (for example per-browser e2e branches), hand the Vite `dist/` over with `stash`/`unstash`.

```groovy
pipeline {
  agent none
  options {
    timeout(time: 45, unit: 'MINUTES')
    disableConcurrentBuilds(abortPrevious: true)      // = concurrency: cancel-in-progress
    buildDiscarder(logRotator(numToKeepStr: '50'))
  }
  stages {
    stage('Select') { /* section 4 */ }
    stage('Test and build') {
      parallel {
        stage('static-checks') {
          agent { kubernetes { yamlFile 'ci/jenkins/pod.yaml'; defaultContainer 'build' } }
          steps { sh 'python3 libs/shared-schemas/codegen.py --check && cd apps/web && npm ci && npm run lint && npm run typecheck' }
        }
        stage('orders-unit') {
          when { expression { return env.ORDERS_UNIT != '' } }
          agent { kubernetes { yamlFile 'ci/jenkins/pod.yaml'; defaultContainer 'build' } }
          steps { sh 'cd apps/orders-api && ./mvnw -B verify -DskipITs -Dsurefire.failIfNoSpecifiedTests=false -Dtest="$ORDERS_UNIT"' }
          post { always { junit testResults: 'apps/orders-api/target/surefire-reports/*.xml', allowEmptyResults: true } }
        }
        stage('web') {
          agent { kubernetes { yamlFile 'ci/jenkins/pod.yaml'; defaultContainer 'build' } }
          stages {
            stage('web-build') { steps { sh 'cd apps/web && npm ci && npm run build' } }
            stage('web-e2e')   { steps { sh 'cd apps/web && npx playwright test' } }   // same pod, reuses dist/
          }
          post { always { junit testResults: 'apps/web/reports/*.xml', allowEmptyResults: true } }
        }
        // analytics-test, images: same pattern
      }
    }
    stage('Publish') { /* push images from the BuildKit cache, only if everything above passed */ }
  }
}
```

### 3.2 Duration-balanced shards with `shardkit` (dynamic fan-out)

Declarative `matrix` axes are static, and a `matrix` cannot sit inside a parallel branch. For sharded suites,
build the branches in a `script` block and call the scripted `parallel` step. `shardkit --index` is 0-based.

```groovy
stage('Test and build') {
  steps {
    script {
      def branches = [:]
      int n = 2                                            // shard count: tune with the shard-count curve
      for (int i = 0; i < n; i++) {
        int idx = i                                        // capture the value, not the loop variable
        branches["orders-it-${idx}"] = {
          inPod {
            writeFile file: 'units.txt', text: env.ORDERS_IT
            def classes = sh(returnStdout: true, script: """
              \$SHARDKIT plan --framework junit --durations experiments/durations/orders-it.json \
                --units-file units.txt --shards ${n} --index ${idx} --style maven""").trim()
            if (classes) {
              sh "cd apps/orders-api && ./mvnw -B verify -Dtest=NoUnitTestsInThisShard " +
                 "-Dsurefire.failIfNoSpecifiedTests=false -Dit.test=${classes}"
            }
            junit testResults: 'apps/orders-api/target/failsafe-reports/*.xml', allowEmptyResults: true
          }
        }
      }
      // web-unit and analytics shards: same loop with --framework vitest|pytest --style args
      branches['static-checks'] = { inPod { sh 'python3 libs/shared-schemas/codegen.py --check' } }
      parallel branches                                    // add failFast: true to the map only if you want early abort
    }
  }
}
```

Playwright can shard itself with `npx playwright test --shard=${idx + 1}/${n}` (Playwright's index is 1-based).
Splitting by browser project (`--project=chromium|firefox|webkit`), as `ci-parallel.yml` does, is the other option.

### 3.3 Alternative: Parallel Test Executor `splitTests`

`splitTests` "analyzes test results from the last successful build of this job" and returns roughly equal
splits. `parallelism` is `count` (N buckets) or `time` (minutes per bucket). With `generateInclusions: true` each
split has `includes` (boolean) and `list` (patterns). `stage` limits the history to one stage.

```groovy
def splits = splitTests parallelism: count(4), generateInclusions: true, stage: 'orders-it'   // count(4) symbol form unverified
def branches = [:]
splits.eachWithIndex { s, i ->
  branches["orders-it-${i}"] = {
    inPod {
      writeFile file: 'apps/orders-api/split.txt', text: s.list.join('\n')
      def prop = s.includes ? 'surefire.includesFile' : 'surefire.excludesFile'
      sh "cd apps/orders-api && ./mvnw -B test -D${prop}=split.txt"
      junit 'apps/orders-api/target/surefire-reports/*.xml'
    }
  }
}
parallel branches
```

When to prefer which: `splitTests` needs no durations file but only knows what the **previous successful build
of the same job** recorded, works naturally for Java class patterns, and is awkward for Vitest/pytest file
units. `shardkit` reads a versioned durations snapshot, handles all three frameworks the same way, and composes
with `tia` (shard only the selected units). The `failsafe` (`*IT`) suite would need `failsafe.includesFile`
instead (unverified).

**Caveats.**
- Each branch is a new pod: checkout, cache restore and toolchain warm-up repeat per branch. The warm image
  and a shallow clone (Git plugin clone options) keep this small, but measure it before raising N.
- Nesting a scripted `parallel` inside a parallel branch (for example per-browser e2e under the web branch) is
  outside what the declarative syntax page covers (unverified). Keep one flat `parallel` map where possible.
- `stash` is "designed for use with small files" and "between 5-100 MB you should probably consider
  alternatives". The Vite `dist/` fits; Maven `target/` or `node_modules` do not. Use the cache or a
  repository manager for those.

---

## 4. Test impact analysis with `tia`

**Mechanism.** Jenkins has no built-in test selection. `when { changeset "apps/web/**" }` skips whole stages
based on the build's SCM changeset, which is coarse and compares against what Jenkins last built rather than
the PR's merge base (unverified for every branch source). Use it at most as a pre-filter. Run `tia` in a first
stage and gate stages on its output:

```groovy
stage('Select') {
  agent { kubernetes { yamlFile 'ci/jenkins/pod.yaml'; defaultContainer 'build' } }
  steps {
    script {
      env.POD_YAML = readFile('ci/jenkins/pod.yaml')
      if (env.BRANCH_NAME == 'main') {                       // safety net: main always runs everything
        sh "\$TIA select --config tia.toml --force-full 'main branch safety net' --out selection.json"
      } else {
        def target = env.CHANGE_TARGET ?: 'main'             // set for change-request builds
        sh "git fetch --no-tags origin +refs/heads/${target}:refs/remotes/origin/${target}"
        sh "\$TIA select --config tia.toml --base \$(git merge-base origin/${target} HEAD) --head HEAD --out selection.json"
      }
      def show = { app, suite, style ->
        sh(returnStdout: true, script: "\$TIA show --selection selection.json --app ${app} --suite ${suite} --style ${style}").trim()
      }
      env.ORDERS_UNIT = show('orders-api', 'unit', 'maven')
      env.ORDERS_IT   = show('orders-api', 'integration', 'maven')
      env.WEB_UNIT    = show('web', 'unit', 'args')
      env.WEB_E2E     = show('web', 'e2e', 'args')
      env.ANALYTICS   = show('analytics', 'unit', 'args')
    }
    archiveArtifacts artifacts: 'selection.json'            // audit trail: what was skipped and why
  }
}
```

Stages then use `when { expression { return env.WEB_UNIT != '' } }`. The `expression` must return a boolean or
`null`, since the strings `"0"` and `"false"` are truthy. The nightly job (a separate Pipeline with a `cron`
trigger) runs `--force-full` and rebuilds the coverage maps exactly as `nightly-full.yml` does.

**Caveats.**
- `tia` needs the merge base. Multibranch checkouts often fetch only the built branch, hence the explicit
  `git fetch`. If credentials make that awkward, write the changed paths from the SCM to a file and use
  `tia select --changed changed.txt`.
- `CHANGE_TARGET` is set only for change-request builds and only if the branch source supports it. Plain branch
  builds fall back to `main` above.
- Keep `tia.toml` and `experiments/coverage/*.json` in the repository so selection is reproducible per commit.

---

## 5. Test results and `shardkit` durations: JUnit plugin

**Mechanism.** `junit testResults: '<Ant glob>'` records results, failing the build on missing results unless
`allowEmptyResults: true` (required for shards or TIA subsets that may run nothing). The JUnit plugin is also the
data source for `splitTests`.

RetailOps report paths: `apps/orders-api/target/surefire-reports/*.xml`,
`apps/orders-api/target/failsafe-reports/*.xml`, `apps/web/reports/junit.xml` (Vitest `junit` reporter, set in
`vite.config.ts`), `apps/web/reports/e2e-junit.xml` (Playwright `junit` reporter), and `apps/analytics/reports/junit.xml`
(`pytest --junitxml`).

Feeding `shardkit`: in the nightly full-suite job, after the tests and before the pod is deleted:

```groovy
sh '''
  $SHARDKIT durations --framework junit --junit 'apps/orders-api/target/failsafe-reports/*.xml' --out out/orders-it.json
  $SHARDKIT durations --framework pytest --junit 'apps/analytics/reports/*.xml' --root apps/analytics --out out/analytics.json
'''
archiveArtifacts artifacts: 'out/*.json'
```

A named owner reviews the change and commits it to `experiments/durations/` (README §3.4). Do not let PR builds
rewrite durations: a failing or partial run produces skewed timings.

---

## 6. Profiling with `cipro`

**Current state.** `cipro fetch` and `cipro logs` speak only the GitHub REST API (`tools/cipro/src/cipro/github.py`).
Nothing in this repository fetches Jenkins data yet. Everything downstream (`summary`, `report`, `compare`,
`export`) reads the SQLite tables `runs`, `jobs` and `steps` (`store.py`), so a Jenkins adapter only has to fill
those tables and archive the raw JSON, as ADR-0004 requires.

**What an adapter would need (Pipeline: Stage View REST API, plus Jenkins' generic JSON API):**

| cipro table | Jenkins source | Fields |
|---|---|---|
| `runs` | `GET /job/<job>/wfapi/runs` (multibranch: `/job/<repo>/job/<branch>/wfapi/runs`) | `id`, `name`, `status`, `startTimeMillis`, `endTimeMillis`, `durationMillis` |
| `jobs` | `GET /job/<job>/<n>/wfapi/describe` → `stages[]` | per stage: `name`, `status`, `startTimeMillis`, `durationMillis` |
| `steps` | `GET /job/<job>/<n>/execution/node/<id>/wfapi/describe` → `stageFlowNodes[]` | per step node: name, status, timings |
| `runs.head_sha` | `GET /job/<job>/<n>/api/json` (Git plugin build data) | commit SHA; the exact field path is unverified |
| logs (`cipro logs`) | `GET /job/<job>/<n>/consoleText` (unverified) | parse cache hit/miss and test counts as today |

Gaps to handle honestly:
- **Queue time.** The Stage View API docs sample shows start/end/duration only. Queue time per pod (pod
  pending → agent online) is not in those fields (a `queueDurationMillis` field is unverified). Measure it from
  Kubernetes pod events, or mark it "not measured".
- **Parallel branches** appear as stages or parallel nodes, not as separate jobs. The adapter must map each
  branch to a `jobs` row so that critical path and job-seconds keep their meaning.
- **Cost.** Jenkins has no billable minutes. Use the self-hosted model of ADR-0007 (pod CPU-seconds × a cited
  VM price), with prices recorded in `pricing.toml` with source and date.
- **Step names.** The waste breakdown classifies steps by name (`classify.py`). Name `sh` steps with
  `label:` (for example `sh label: 'orders-api - install', script: '...'`; the `label` parameter is unverified)
  so they land in the right bucket.
- **Authentication.** HTTP Basic with a user API token, as the Remote Access API page describes.

---

## 7. Checklist specific to Jenkins

- [ ] Start with the repository manager and the warm pod image: they help every job without restructuring.
- [ ] `disableConcurrentBuilds(abortPrevious: true)` on PR jobs, but not on `main` if every commit must be built.
- [ ] Every parallel branch publishes JUnit with `allowEmptyResults: true`; no fail-fast on test shards, so every shard reports.
- [ ] `main` and the nightly job always run `tia select --force-full`.
- [ ] Measure pod start-up per branch before increasing the shard count (README §3.5).

---

## References

All accessed 2026-10-25.

- Jenkins, Pipeline Syntax (declarative `parallel`, `failFast`, `matrix`, `options`, `when`, `agent kubernetes`): https://www.jenkins.io/doc/book/pipeline/syntax/
- Jenkins, Pipeline: Basic Steps (`stash`, `unstash`): https://www.jenkins.io/doc/pipeline/steps/workflow-basic-steps/
- Jenkins, JUnit plugin step reference (`junit`): https://www.jenkins.io/doc/pipeline/steps/junit/
- Jenkins, Parallel Test Executor plugin: https://plugins.jenkins.io/parallel-test-executor/
- Jenkins, Parallel Test Executor step reference (`splitTests`): https://www.jenkins.io/doc/pipeline/steps/parallel-test-executor/
- Jenkins, Kubernetes plugin (pod per agent, `POD_LABEL`, `defaultContainer`, workspace volumes, `idleMinutes`): https://plugins.jenkins.io/kubernetes/
- Jenkins, Job Cacher plugin (`cache`, `arbitraryFileCache`, storage backends): https://plugins.jenkins.io/jobcacher/
- Jenkins, Pipeline Stage View REST API: https://github.com/jenkinsci/pipeline-stage-view-plugin/blob/master/rest-api/README.md
- Jenkins, Remote Access API: https://www.jenkins.io/doc/book/using/remote-access-api/
- Jenkins, Branches and Pull Requests (multibranch, `CHANGE_*` variables): https://www.jenkins.io/doc/book/pipeline/multibranch/
- Apache Maven, Using Mirrors for Repositories: https://maven.apache.org/guides/mini/guide-mirror-settings.html
- Apache Maven Surefire, `surefire:test` parameters (`includesFile`, `excludesFile`, `failIfNoSpecifiedTests`): https://maven.apache.org/surefire/maven-surefire-plugin/test-mojo.html
- Docker, Registry cache backend: https://docs.docker.com/build/cache/backends/registry/
- BuildKit README (`buildctl build`, `--opt filename`, registry cache, daemonless mode): https://github.com/moby/buildkit/blob/master/README.md
- Playwright, Sharding: https://playwright.dev/docs/test-sharding
