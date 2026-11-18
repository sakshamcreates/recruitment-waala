import assert from "node:assert/strict";
import { test } from "node:test";
import { mapOpportunity, mapPage } from "../lib/catalogue/api-adapter.ts";

const notice = {
  id: "de1f0fe0-e1c0-4f94-8a0b-ecac4fc22a78",
  title: "Integration test record",
  organisation: "Test issuer",
  status: "published",
  published_at: "2026-01-01T20:00:00Z",
  deadline: null,
  details: { category: "government_job", vacancies: null },
  provenance: { source: "test-source", verified_at: null, official_url: null },
  apply_url: "javascript:alert(1)",
};

test("maps the API record into category-specific rendering data", () => {
  const job = mapOpportunity(notice);
  assert.equal(job.category, "government-jobs");
  assert.equal(job.publishedOn, "2026-01-02");
  assert.equal(job.deadline, undefined);
  assert.equal(job.applyUrl, undefined);
  assert.deepEqual(job.provenance, {
    kind: "official",
    source: "test-source",
    officialUrl: undefined,
    verifiedOn: undefined,
  });
});

test("maps an empty page and rejects malformed/error payloads", () => {
  assert.deepEqual(
    mapPage({ items: [], total: 0, page: 1, limit: 5, facets: {} }),
    {
      items: [],
      total: 0,
      page: 1,
      limit: 5,
      facets: {},
    },
  );
  assert.throws(() => mapPage({ status: 503, detail: "Unavailable" }));
  assert.throws(() => mapOpportunity({ ...notice, status: "draft" }));
});

test("suppresses approved-format application links on withdrawn records", () => {
  const record = mapOpportunity({
    ...notice,
    status: "withdrawn",
    apply_url: "https://www.upsc.gov.in/",
  });
  assert.equal(record.applyUrl, undefined);
});
