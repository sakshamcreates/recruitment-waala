import assert from "node:assert/strict";
import { test } from "node:test";
import { demoDate, fixtures } from "../lib/catalogue/fixtures.ts";
import {
  paginate,
  readSearch,
  searchCatalogue,
  searchHref,
} from "../lib/catalogue/search.ts";

const state = (query: string) => readSearch(new URLSearchParams(query));

test("keyword matching combines title and skills without case sensitivity", () => {
  const items = searchCatalogue(
    fixtures,
    state("q=FRONTEND+typescript"),
    demoDate,
  );
  assert.deepEqual(
    items.map(({ id }) => id),
    ["frontend-engineer"],
  );
});

test("state, qualification, type and organisation facets intersect", () => {
  const query =
    "category=government-jobs&state=Maharashtra&qualification=Diploma&type=Contract&organisation=Western+Infrastructure+Board";
  const items = searchCatalogue(fixtures, state(query), demoDate);
  assert.deepEqual(
    items.map(({ id }) => id),
    ["technical-assistant"],
  );
});

test("deadline filter uses the demo reference date and excludes missing deadlines", () => {
  const items = searchCatalogue(
    fixtures,
    state("deadline=week&sort=deadline"),
    demoDate,
  );
  assert.deepEqual(
    items.map(({ id }) => id),
    ["assistant-audit-officer", "technical-assistant"],
  );
});

test("sorting is stable and missing deadlines sort last", () => {
  const newest = searchCatalogue(fixtures, state(""), demoDate);
  assert.deepEqual(
    newest.slice(0, 3).map(({ id }) => id),
    ["accounts-exam-result", "assistant-audit-officer", "frontend-engineer"],
  );
  const deadline = searchCatalogue(fixtures, state("sort=deadline"), demoDate);
  assert.equal(deadline[0].id, "assistant-audit-officer");
  assert.equal(deadline.at(-1)?.deadline, undefined);
  const titles = searchCatalogue(fixtures, state("sort=title"), demoDate).map(
    ({ title }) => title,
  );
  assert.deepEqual(
    titles,
    [...titles].sort((a, b) => a.localeCompare(b, "en-IN")),
  );
});

test("URL state round-trips and drops defaults", () => {
  const original = state(
    "q=React%20%26%20TypeScript&category=corporate-jobs&sort=title&page=2&mode=Hybrid",
  );
  const href = searchHref("/search", original);
  assert.deepEqual(
    readSearch(new URL(href, "https://example.invalid").searchParams),
    original,
  );
  assert.equal(
    searchHref(
      "/search",
      state("page=-4&sort=nope&category=constructor&deadline=invalid&foo=bar"),
    ),
    "/search",
  );
});

test("pagination clamps out-of-range pages and handles empty results", () => {
  const result = paginate(fixtures, 999);
  assert.equal(result.page, 4);
  assert.equal(result.items.length, 1);
  assert.deepEqual(paginate([], 2), {
    page: 1,
    totalPages: 1,
    start: 0,
    items: [],
  });
});
