# ADR-0003: Toolchain versions

**Status:** accepted

| Tool | CI version | Local (author machine) |
|---|---|---|
| Java | Temurin 21 (`actions/setup-java`) | Temurin 21.0.12.1 zip in `C:\Users\<user>\tools` |
| Maven | Maven Wrapper in `apps/orders-api` | 3.9.9 zip, used only to generate the wrapper |
| Node | 20 LTS | 22 (compatible) |
| Python | 3.12 | 3.13 (compatible) |
| Docker | runner-provided | Docker Desktop 28 (WSL2) |

`winget` is not available on the author machine, so JDK and Maven were downloaded as zips from Adoptium and
the Apache archive with checksum verification. CI is the source of truth for all timings.
