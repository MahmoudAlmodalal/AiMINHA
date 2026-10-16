# Implemented API contracts

`openapi.json` and `src/generated.ts` are generated artifacts. Change annotated DRF views/serializers, run `make contracts`, then review both diffs. `make contracts-check` regenerates to a temporary directory and rejects stale output or drift from the architecture Problem schema. The single bootstrap health route is explicitly scoped by Phase 05; new product routes must conform to the architecture baseline before activation.

[The architecture OpenAPI](../../docs/architecture/openapi.json) remains the future product design. It is deliberately not exposed/generated as a callable frontend SDK: Phase 06–17 operations do not exist yet. The client uses same-origin credentials and validates the small health response at runtime; generated TypeScript is not a substitute for runtime validation or authorization on future payloads. No third-party network request or telemetry is included.
