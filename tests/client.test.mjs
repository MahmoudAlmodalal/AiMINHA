import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  createHealthClient,
  getHealth,
  getCsrf,
  validateSession,
  parseAttachment,
  calculateTotalPages,
  formatAttachmentMarkup,
} from "../packages/contracts/src/index.ts";

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

test("attachment parsing carries display_name and validates API payload fields", () => {
  const valid = {
    id: "00000000-0000-4000-8000-000000000001",
    asset_id: "00000000-0000-4000-8000-000000000002",
    display_name: "cv.pdf",
    state: "SHARED",
    version: 1,
    created_at: "2026-10-20T12:00:00Z",
  };
  const parsed = parseAttachment(valid);
  assert.equal(parsed.id, valid.id);
  assert.equal(parsed.asset_id, valid.asset_id);
  assert.equal(parsed.display_name, "cv.pdf");
  assert.equal(parsed.state, "SHARED");
  assert.equal(parsed.version, 1);
  assert.equal(parsed.created_at, valid.created_at);

  const revoked = parseAttachment({ ...valid, state: "REVOKED" });
  assert.equal(revoked.state, "REVOKED");

  // Rejects missing or invalid display_name
  assert.throws(() => parseAttachment({ ...valid, display_name: undefined }), /INVALID_ATTACHMENT_DISPLAY_NAME/);
  assert.throws(() => parseAttachment({ ...valid, display_name: null }), /INVALID_ATTACHMENT_DISPLAY_NAME/);
  assert.throws(() => parseAttachment({ ...valid, display_name: 12345 }), /INVALID_ATTACHMENT_DISPLAY_NAME/);
  assert.throws(() => parseAttachment({ ...valid, display_name: "a".repeat(256) }), /INVALID_ATTACHMENT_DISPLAY_NAME/);

  // Rejects invalid id or asset_id
  assert.throws(() => parseAttachment({ ...valid, id: "invalid-uuid" }), /INVALID_ATTACHMENT_ID/);
  assert.throws(() => parseAttachment({ ...valid, asset_id: "invalid-uuid" }), /INVALID_ATTACHMENT_ASSET_ID/);

  // Rejects invalid state or version or date
  assert.throws(() => parseAttachment({ ...valid, state: "PENDING" }), /INVALID_ATTACHMENT_STATE/);
  assert.throws(() => parseAttachment({ ...valid, version: 0 }), /INVALID_ATTACHMENT_VERSION/);
  assert.throws(() => parseAttachment({ ...valid, created_at: "not-a-date" }), /INVALID_ATTACHMENT_CREATED_AT/);
  assert.throws(() => parseAttachment(null), /INVALID_ATTACHMENT_RESPONSE/);
});

test("attachment rendering lists display name with asset identifier as secondary detail and visible revoked state in RTL and LTR", () => {
  const sharedItem = {
    id: "00000000-0000-4000-8000-000000000001",
    asset_id: "00000000-0000-4000-8000-000000000002",
    display_name: "transcript_official.pdf",
    state: "SHARED",
    version: 1,
    created_at: "2026-10-20T12:00:00Z",
  };
  const revokedItem = { ...sharedItem, state: "REVOKED" };

  function renderAttachmentNode(item, locale) {
    const ar = locale === "ar";
    return React.createElement(
      "span",
      { className: "badge" },
      React.createElement("strong", null, item.display_name),
      " ",
      React.createElement("small", { className: "secondary-detail" }, `(${item.asset_id.slice(0, 8)})`),
      " ",
      React.createElement("span", { className: "attachment-status" }, item.state === "SHARED" ? (ar ? "مشارك" : "shared") : (ar ? "ملغى" : "revoked")),
      item.state === "SHARED"
        ? React.createElement("button", { type: "button", className: "secondary" }, ar ? "إلغاء المشاركة" : "Revoke")
        : null
    );
  }

  // English LTR shared
  const enShared = renderToStaticMarkup(renderAttachmentNode(sharedItem, "en"));
  assert.match(enShared, /<strong>transcript_official\.pdf<\/strong>/);
  assert.match(enShared, /<small class="secondary-detail">\(00000000\)<\/small>/);
  assert.match(enShared, /<span class="attachment-status">shared<\/span>/);
  assert.match(enShared, /Revoke/);

  // English LTR revoked
  const enRevoked = renderToStaticMarkup(renderAttachmentNode(revokedItem, "en"));
  assert.match(enRevoked, /<strong>transcript_official\.pdf<\/strong>/);
  assert.match(enRevoked, /<small class="secondary-detail">\(00000000\)<\/small>/);
  assert.match(enRevoked, /<span class="attachment-status">revoked<\/span>/);
  assert.doesNotMatch(enRevoked, /Revoke/);

  // Arabic RTL shared
  const arShared = renderToStaticMarkup(renderAttachmentNode(sharedItem, "ar"));
  assert.match(arShared, /<strong>transcript_official\.pdf<\/strong>/);
  assert.match(arShared, /<small class="secondary-detail">\(00000000\)<\/small>/);
  assert.match(arShared, /<span class="attachment-status">مشارك<\/span>/);
  assert.match(arShared, /إلغاء المشاركة/);

  // Arabic RTL revoked
  const arRevoked = renderToStaticMarkup(renderAttachmentNode(revokedItem, "ar"));
  assert.match(arRevoked, /<strong>transcript_official\.pdf<\/strong>/);
  assert.match(arRevoked, /<small class="secondary-detail">\(00000000\)<\/small>/);
  assert.match(arRevoked, /<span class="attachment-status">ملغى<\/span>/);
  assert.doesNotMatch(arRevoked, /إلغاء المشاركة/);

  // Markup formatter helper
  assert.equal(
    formatAttachmentMarkup(sharedItem, "en"),
    '<strong>transcript_official.pdf</strong> <small class="secondary-detail">(00000000)</small> <span class="attachment-status">shared</span>'
  );
  assert.equal(
    formatAttachmentMarkup(revokedItem, "ar"),
    '<strong>transcript_official.pdf</strong> <small class="secondary-detail">(00000000)</small> <span class="attachment-status">ملغى</span>'
  );
});

test("ticket pagination calculation derives totalPages from response total and page_size", () => {
  assert.equal(calculateTotalPages(0, 20), 1);
  assert.equal(calculateTotalPages(1, 20), 1);
  assert.equal(calculateTotalPages(20, 20), 1);
  assert.equal(calculateTotalPages(21, 20), 2);
  assert.equal(calculateTotalPages(40, 20), 2);
  assert.equal(calculateTotalPages(41, 20), 3);
  assert.equal(calculateTotalPages(100, 10), 10);
  assert.equal(calculateTotalPages(55, 50), 2);

  assert.throws(() => calculateTotalPages(-1, 20), /INVALID_PAGINATION_ARGUMENTS/);
  assert.throws(() => calculateTotalPages(20, 0), /INVALID_PAGINATION_ARGUMENTS/);
  assert.throws(() => calculateTotalPages(NaN, 20), /INVALID_PAGINATION_ARGUMENTS/);
  assert.throws(() => calculateTotalPages(20, -5), /INVALID_PAGINATION_ARGUMENTS/);
});

test("ticket pagination state handling allows navigating beyond 20 tickets and preserves selected ticket", () => {
  class SupportDeskSimulator {
    constructor() {
      this.page = 1;
      this.pageSize = 20;
      this.total = 0;
      this.totalPages = 1;
      this.rows = [];
      this.selected = null;
    }

    applyListResponse(response) {
      this.rows = response.items;
      this.total = response.total;
      this.pageSize = response.page_size;
      this.page = response.page;
      this.totalPages = calculateTotalPages(response.total, response.page_size);
    }

    selectTicket(item) {
      this.selected = item;
    }

    navigate(nextPage, fetchApi) {
      if (nextPage < 1 || nextPage > this.totalPages || nextPage === this.page) return;
      const response = fetchApi(nextPage, this.pageSize);
      this.applyListResponse(response);
      // NOTE: selected ticket is NOT cleared or lost
    }

    changePageSize(newSize, fetchApi) {
      if (newSize < 1 || newSize === this.pageSize) return;
      const response = fetchApi(1, newSize);
      this.applyListResponse(response);
    }
  }

  const fakeTicketsApi = (targetPage, size) => {
    const totalCount = 45; // 45 tickets total: page 1 has 20, page 2 has 20, page 3 has 5
    const offset = (targetPage - 1) * size;
    const pageItems = Array.from(
      { length: Math.min(size, Math.max(0, totalCount - offset)) },
      (_, idx) => ({
        id: `00000000-0000-4000-8000-${String(offset + idx + 1).padStart(12, "0")}`,
        subject: `Support Ticket #${offset + idx + 1}`,
        state: "NEW",
      })
    );
    return { items: pageItems, total: totalCount, page: targetPage, page_size: size };
  };

  const desk = new SupportDeskSimulator();
  // 1. Initial page 1 load
  desk.applyListResponse(fakeTicketsApi(1, 20));
  assert.equal(desk.page, 1);
  assert.equal(desk.pageSize, 20);
  assert.equal(desk.total, 45);
  assert.equal(desk.totalPages, 3);
  assert.equal(desk.rows.length, 20);
  assert.equal(desk.rows[0].subject, "Support Ticket #1");

  // Previous disabled, Next enabled
  assert.equal(desk.page <= 1, true);
  assert.equal(desk.page >= desk.totalPages, false);

  // Student selects ticket #5
  desk.selectTicket(desk.rows[4]);
  assert.equal(desk.selected.subject, "Support Ticket #5");

  // 2. Navigate to page 2 (reaching beyond the first 20 owned support tickets)
  desk.navigate(2, fakeTicketsApi);
  assert.equal(desk.page, 2);
  assert.equal(desk.rows.length, 20);
  assert.equal(desk.rows[0].subject, "Support Ticket #21");
  // Both Previous and Next enabled
  assert.equal(desk.page <= 1, false);
  assert.equal(desk.page >= desk.totalPages, false);
  // CRITICAL: selected ticket must not be cleared or lost
  assert.ok(desk.selected);
  assert.equal(desk.selected.subject, "Support Ticket #5");

  // 3. Navigate to page 3
  desk.navigate(3, fakeTicketsApi);
  assert.equal(desk.page, 3);
  assert.equal(desk.rows.length, 5);
  assert.equal(desk.rows[0].subject, "Support Ticket #41");
  // Previous enabled, Next disabled
  assert.equal(desk.page <= 1, false);
  assert.equal(desk.page >= desk.totalPages, true);
  // Selected ticket still preserved
  assert.equal(desk.selected.subject, "Support Ticket #5");

  // 4. Navigate back to page 1
  desk.navigate(1, fakeTicketsApi);
  assert.equal(desk.page, 1);
  assert.equal(desk.rows[0].subject, "Support Ticket #1");
  assert.equal(desk.selected.subject, "Support Ticket #5");

  // 5. Change page size to 50
  desk.changePageSize(50, fakeTicketsApi);
  assert.equal(desk.page, 1);
  assert.equal(desk.pageSize, 50);
  assert.equal(desk.totalPages, 1);
  assert.equal(desk.rows.length, 45);
  assert.equal(desk.selected.subject, "Support Ticket #5");
});

test("deletion-impact endpoint can be queried to refresh impact review", async () => {
  let impactCalls = 0;
  const client = createHealthClient(async request => {
    if (request.url.endsWith("/api/v1/account/deletions/impact")) {
      impactCalls++;
      return Response.json({
        policy_id: "00000000-0000-4000-8000-000000000001",
        recovery_days: 30,
        recovery_timezone: "UTC",
        cutoff_algorithm: "CALENDAR_DAY",
        available: true,
      });
    }
    return Response.json({ code: "NOT_FOUND" }, { status: 404 });
  }, "http://localhost");

  const impact1 = await client.GET("/api/v1/account/deletions/impact");
  assert.equal(impact1.response.status, 200);
  assert.equal(impact1.data.recovery_days, 30);
  assert.equal(impact1.data.available, true);
  assert.equal(impactCalls, 1);

  // Refreshing impact without page reload
  const impact2 = await client.GET("/api/v1/account/deletions/impact");
  assert.equal(impact2.response.status, 200);
  assert.equal(impact2.data.recovery_days, 30);
  assert.equal(impactCalls, 2);
});
