import assert from "node:assert/strict";
import test from "node:test";
import { createHealthClient, getHealth } from "../packages/contracts/src/index.ts";

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
