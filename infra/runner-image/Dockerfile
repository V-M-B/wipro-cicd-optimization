# Warm ephemeral runner image for ARC runner scale sets (Phase 5).
# Build context: repository root (so dependency manifests can be pre-fetched):
#   docker build -f infra/runner-image/Dockerfile -t retailops-runner:local .
# Everything a RetailOps job needs is baked in: JDK 21, Maven deps, Node 20 + npm cache,
# Python 3.12 + pip wheels, Playwright browsers with system deps, Docker CLI (DinD sidecar provides the daemon).
ARG RUNNER_VERSION=2.329.0
FROM ghcr.io/actions/actions-runner:${RUNNER_VERSION}

USER root
ENV DEBIAN_FRONTEND=noninteractive \
    JAVA_HOME=/opt/java/openjdk \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright \
    PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PATH=/opt/java/openjdk/bin:/opt/python/bin:$PATH

# OS packages, Node 20, Python 3.12 (deadsnakes is not needed on noble: python3.12 is the default)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl git unzip xz-utils python3 python3-venv python3-pip \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Temurin JDK 21 from the official image
COPY --from=eclipse-temurin:21-jdk /opt/java/openjdk /opt/java/openjdk

# Python venv on PATH so `pip install` works without --break-system-packages
RUN python3 -m venv /opt/python && chown -R runner:runner /opt/python

# Pre-warm dependency caches from the repository's manifests
WORKDIR /tmp/warm
COPY apps/orders-api/pom.xml apps/orders-api/mvnw orders/
COPY apps/orders-api/.mvn orders/.mvn
COPY apps/web/package.json apps/web/package-lock.json web/
COPY apps/analytics/requirements.txt apps/analytics/requirements-dev.txt analytics/
RUN chown -R runner:runner /tmp/warm
USER runner
RUN cd orders && ./mvnw -B -q dependency:go-offline -DexcludeReactor=true \
    && cd ../web && npm ci --no-audit --no-fund && npx playwright --version \
    && cd ../analytics && pip install -r requirements-dev.txt
USER root
RUN cd /tmp/warm/web && npx playwright install --with-deps chromium firefox webkit \
    && chmod -R a+rx /opt/ms-playwright \
    && rm -rf /tmp/warm/web/node_modules /var/lib/apt/lists/*
USER runner
WORKDIR /home/runner
