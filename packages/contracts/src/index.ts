import createClient from "openapi-fetch";
import type { paths, components } from "./generated.js";
export type { components } from "./generated.js";

export type Health = components["schemas"]["Health"];
export type Problem = components["schemas"]["Problem"];
export type Session = components["schemas"]["Session"];
export type Attachment = components["schemas"]["Attachment"];
export type AttachmentState = components["schemas"]["AttachmentStateEnum"];
export type Ticket = components["schemas"]["Ticket"];
export type TicketPage = components["schemas"]["TicketPage"];

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function parseAttachment(value: unknown): Attachment {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("INVALID_ATTACHMENT_RESPONSE");
  }
  const row = value as Record<string, unknown>;
  if (typeof row.id !== "string" || !UUID_PATTERN.test(row.id)) {
    throw new Error("INVALID_ATTACHMENT_ID");
  }
  if (typeof row.asset_id !== "string" || !UUID_PATTERN.test(row.asset_id)) {
    throw new Error("INVALID_ATTACHMENT_ASSET_ID");
  }
  if (typeof row.display_name !== "string" || row.display_name.length > 255) {
    throw new Error("INVALID_ATTACHMENT_DISPLAY_NAME");
  }
  if (row.state !== "SHARED" && row.state !== "REVOKED") {
    throw new Error("INVALID_ATTACHMENT_STATE");
  }
  if (!Number.isSafeInteger(row.version) || Number(row.version) < 1) {
    throw new Error("INVALID_ATTACHMENT_VERSION");
  }
  if (typeof row.created_at !== "string" || !/(?:[zZ]|[+-]\d{2}:\d{2})$/.test(row.created_at) || !Number.isFinite(Date.parse(row.created_at))) {
    throw new Error("INVALID_ATTACHMENT_CREATED_AT");
  }
  return {
    id: row.id,
    asset_id: row.asset_id,
    display_name: row.display_name,
    state: row.state as "SHARED" | "REVOKED",
    version: Number(row.version),
    created_at: row.created_at,
  };
}

export function calculateTotalPages(total: number, pageSize: number): number {
  if (!Number.isSafeInteger(total) || total < 0 || !Number.isSafeInteger(pageSize) || pageSize < 1) {
    throw new Error("INVALID_PAGINATION_ARGUMENTS");
  }
  return Math.max(1, Math.ceil(total / pageSize));
}

export function formatAttachmentMarkup(
  item: { display_name: string; asset_id: string; state: "SHARED" | "REVOKED" },
  locale: "ar" | "en"
): string {
  const ar = locale === "ar";
  const stateLabel = item.state === "SHARED" ? (ar ? "مشارك" : "shared") : (ar ? "ملغى" : "revoked");
  return `<strong>${item.display_name}</strong> <small class="secondary-detail">(${item.asset_id.slice(0, 8)})</small> <span class="attachment-status">${stateLabel}</span>`;
}

export function createHealthClient(fetchImplementation: typeof fetch = globalThis.fetch, baseUrl = "") {
  return createClient<paths>({ baseUrl, fetch: fetchImplementation, credentials: "same-origin", cache: "no-store" });
}

export async function getHealth(client = createHealthClient()): Promise<Health> {
  const { data, error, response } = await client.GET("/api/v1/health");
  if (!response.ok || error || !data || data.status !== "ok" || Object.keys(data).length !== 1) {
    throw new Error("HEALTH_UNAVAILABLE");
  }
  return data;
}

export async function getCsrf(client = createHealthClient()): Promise<string> {
  const { data, response } = await client.GET("/api/v1/session/csrf");
  if (!response.ok || !data || typeof data.csrf_token !== "string" || !data.csrf_token) {
    throw new Error("CSRF_UNAVAILABLE");
  }
  return data.csrf_token;
}

export function validateSession(value: Session): Session {
  const allowed = ["actor_id", "verified_email", "adult_eligible", "roles", "expires_at"];
  if (!value || Object.keys(value).length !== allowed.length || Object.keys(value).some(key => !allowed.includes(key)) ||
      typeof value.actor_id !== "string" || !/^[0-9a-f-]{36}$/i.test(value.actor_id) ||
      value.verified_email !== true || value.adult_eligible !== true || !Array.isArray(value.roles) ||
      value.roles.length !== 1 || !["STUDENT", "ADMIN"].includes(value.roles[0]) ||
      !Number.isFinite(Date.parse(value.expires_at))) {
    throw new Error("INVALID_SESSION_RESPONSE");
  }
  return value;
}
