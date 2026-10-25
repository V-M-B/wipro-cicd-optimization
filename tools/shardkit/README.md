# shardkit — duration-balanced test sharding

Splits a test suite into N shards of near-equal duration using test timings from previous JUnit XML reports.
Standard library only.

- **Units:** Java test classes (fully qualified name), Vitest/Playwright spec files, pytest module files.
- **Algorithm:** longest-processing-time-first greedy bin packing (deterministic). Units with no history get
  the median duration of known units. With no history at all it falls back to round-robin.

```bash
pip install -e tools/shardkit[dev]

# 1. Turn JUnit XML from a full run into per-unit durations
shardkit durations --framework junit --junit 'apps/orders-api/target/surefire-reports/*.xml' \
  --out experiments/durations/orders-unit.json

# 2. In shard i of N, select its units and pass them to the runner
classes=$(shardkit plan --framework junit --durations experiments/durations/orders-unit.json \
  --units 'apps/orders-api/src/test/java/**/*Test.java' --shards 4 --index $i --style maven --summary)
./mvnw -B test -Dtest="$classes"

# 3. Compare LPT against naive round-robin for the dissertation
shardkit compare --framework junit --durations experiments/durations/orders-unit.json \
  --units 'apps/orders-api/src/test/java/**/*Test.java' --shards 4
```

Output styles: `lines`, `json`, `maven` (comma-separated, for `-Dtest`), `args` (space-separated paths, for
Vitest, Playwright and pytest). `--strip-prefix` makes file units relative to an app directory.

Tests: `cd tools/shardkit && pytest --cov=shardkit` (16 tests, 98% coverage).
