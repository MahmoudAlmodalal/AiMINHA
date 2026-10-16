import type { components } from "@minhaai/contracts";

export type Funding = components["schemas"]["FundingEnum"];
export type Round = components["schemas"]["PublicRound"];
export type PublicScholarship = components["schemas"]["PublicScholarship"];
export type Source = components["schemas"]["Source"];
export type AdminScholarship = components["schemas"]["AdminScholarship"];
export type Candidate = Omit<components["schemas"]["Candidate"],
  "id" | "version" | "source_revision_id" | "content_hash" | "created_at" | "created_by" | "duplicate_ids">;
