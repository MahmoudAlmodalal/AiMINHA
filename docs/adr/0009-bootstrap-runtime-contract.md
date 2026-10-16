# ADR 0009 — schema for implemented runtime surface

Status: accepted for the bounded Phase 05 bootstrap after owner confirmation. Traces: Phase 05 work items 3–4, ADR 0002 and `docs/architecture/api-contracts.md` Protocol.

The architecture OpenAPI describes future product endpoints; generating a callable client for all of it now would advertise unimplemented operations. Annotated DRF views generate a separate, explicitly scoped runtime artifact and TypeScript client. CI rejects stale generation, unauthorized Phase 05 routes and structural drift in the shared Problem schema against the architecture baseline. The only bootstrap route is public liveness; future product endpoints require deliberate conformance and phase authorization. The architecture draft is not a second editable runtime specification.

Traceability and the explicit subset cost an extra compatibility check, but avoid silently replacing the product design with a one-endpoint schema. No existing source or prior-phase contract is rewritten. No new glossary term is needed: the domain language remains unchanged.
