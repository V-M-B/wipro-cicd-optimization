# syntax=docker/dockerfile:1
# Baseline image build for orders-api.
# NOTE: intentionally naive layer ordering (whole source copied before the build, so every source
# change re-downloads all Maven dependencies). Phase 2 of the project optimises this; keep as-is
# for the baseline measurements.

FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /workspace
COPY . .
RUN mvn -B -DskipTests package

FROM eclipse-temurin:21-jre
RUN groupadd --system app && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build /workspace/target/orders-api-*.jar /app/orders-api.jar
USER app
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/orders-api.jar"]
