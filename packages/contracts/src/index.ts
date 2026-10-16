import createClient from "openapi-fetch";
import type { paths, components } from "./generated.js";
export type { components } from "./generated.js";

export type Health = components["schemas"]["Health"];
export type Problem = components["schemas"]["Problem"];
export type Session = components["schemas"]["Session"];

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
