import assert from "node:assert/strict";
import test from "node:test";
import { createHealthClient, getHealth, getCsrf, validateSession } from "../packages/contracts/src/index.ts";

test("typed health client uses only the same-origin path and no-store credentials", async () => {
  const client = createHealthClient(async (request) => {
    assert.equal(request.url, "http://localhost/api/v1/health");
    assert.equal(request.credentials, "same-origin");
    assert.equal(request.cache, "no-store");
    return Response.json({ status: "ok" });
  }, "http://localhost");
  assert.deepEqual(await getHealth(client), { status: "ok" });
});

for (const data of [{ status: "bad" }, { status: "ok", private_data: "unexpected" }, null]) {
  test(`malformed health response is rejected: ${JSON.stringify(data)}`, async () => {
    const client = createHealthClient(async () => Response.json(data), "http://localhost");
    await assert.rejects(getHealth(client), /HEALTH_UNAVAILABLE/);
  });
}

test("API failure is never reported as healthy", async () => {
  const client = createHealthClient(async () => Response.json({ code: "INTERNAL_ERROR" }, { status: 500 }), "http://localhost");
  await assert.rejects(getHealth(client), /HEALTH_UNAVAILABLE/);
});

test("identity requests send CSRF only as a header with same-origin cookies", async () => {
  const client = createHealthClient(async request => {
    if (request.method === "GET") return Response.json({ csrf_token: "synthetic-csrf" });
    assert.equal(request.credentials, "same-origin");
    assert.equal(request.headers.get("X-CSRFToken"), "synthetic-csrf");
    assert.equal(new URL(request.url).search, "");
    return Response.json({ accepted: true, correlation_id: "00000000-0000-4000-8000-000000000001" });
  }, "http://localhost");
  const csrf = await getCsrf(client);
  const response = await client.POST("/api/v1/auth/registrations", {
    body: { email: "synthetic@example.invalid", password: "synthetic-only", birth_date: "2000-01-01", locale: "en" },
    params: { header: { "X-CSRFToken": csrf, "Idempotency-Key": "synthetic-operation-key" } }
  });
  assert.equal(response.response.status, 200);
});

test("malformed masked CSRF response is rejected", async () => {
  const client = createHealthClient(async () => Response.json({ csrf_token: null }), "http://localhost");
  await assert.rejects(getCsrf(client), /CSRF_UNAVAILABLE/);
});

test("session payload rejects injected roles, unverified flags and secret fields", () => {
  const session = { actor_id: "00000000-0000-4000-8000-000000000001", verified_email: true,
    adult_eligible: true, roles: ["STUDENT"], expires_at: "2026-10-20T12:00:00Z" };
  assert.deepEqual(validateSession(session), session);
  for (const change of [{ roles: ["SUPERUSER"] }, { verified_email: false }, { password: "unexpected" }]) {
    assert.throws(() => validateSession({ ...session, ...change }), /INVALID_SESSION_RESPONSE/);
  }
});
