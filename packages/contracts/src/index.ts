import createClient from "openapi-fetch";
import type { paths, components } from "./generated.js";

export type Health = components["schemas"]["Health"];
export type Problem = components["schemas"]["Problem"];

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
