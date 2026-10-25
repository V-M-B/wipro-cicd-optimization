# shared-schemas

JSON Schemas for the RetailOps domain, and a dependency-free generator that emits:

- Java records and enums into `apps/orders-api/src/main/java/com/retailops/schemas/`
- TypeScript types into `apps/web/src/generated/schemas.ts`
- Pydantic models into `apps/analytics/app/generated/schemas.py`

Generated files are committed. CI runs `python libs/shared-schemas/codegen.py --check` to fail on stale output.
A change here impacts all three services, which is what makes it interesting for test impact analysis.
