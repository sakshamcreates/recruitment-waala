# Himalayas activation and first publication

Himalayas permits own-site display under its API terms, including commercial
use, subject to linked source credit, its exact Apply URL, limits, expiry
removal, and its prohibition on syndication. Recruitment Waala still requires
a recorded internal operator decision before enabling polling. No production
source or jobs are created by installation. The web UI links the credit to
Himalayas and uses the checked original Apply URL. Detail pages use noindex.
The integration has no exports, feeds, or JobPosting structured data.

References reviewed on 18 November 2026: [API reference](https://himalayas.app/docs/remote-jobs-api),
[API schema](https://himalayas.app/docs/openapi.json),
[data dictionary](https://himalayas.app/docs/data-dictionary), and
[API terms, clause 113](https://himalayas.app/terms).

## Record approval and register

1. Record the operator, approval date, clause 113 basis, own-site-only
   distribution, linked credit, exact Apply link, and rate limits in the
   permission record. Export its reference as `APPROVAL_REF`.
2. Provision the provider organisation using the restricted database role.
   The worker creates separate employers from provider company slugs.

```sql
INSERT INTO organisations (slug, name, official_url)
VALUES ('himalayas-provider', 'Himalayas', 'https://himalayas.app')
ON CONFLICT (slug) DO NOTHING;
SELECT id FROM organisations WHERE slug = 'himalayas-provider';
```

3. Use the returned UUID as `PROVIDER_ORG_ID`. Use the existing private
   editorial instance with `RW_ENV=infrastructure` or `development`,
   `RW_ADMIN_ENABLED=true`, and an exported `RW_ADMIN_TOKEN`.

```sh
INGESTION_API=http://127.0.0.1:8000/api/v1/admin/ingestion
jq -n --arg org "$PROVIDER_ORG_ID" --arg approval "$APPROVAL_REF" '{
  slug: "himalayas",
  organisation_id: $org,
  endpoint_url: "https://himalayas.app/jobs/api",
  enabled: false,
  config: {
    adapter: "himalayas", extraction: "json",
    approval_reference: $approval,
    terms: "https://himalayas.app/terms clause 113, own-site display only",
    fetch_prefixes: ["https://himalayas.app/jobs/api"],
    notice_prefixes: ["https://himalayas.app/companies"],
    application_prefixes: ["https://himalayas.app/companies"],
    interval_seconds: 86400, request_interval_seconds: 2,
    himalayas_pages: 2, himalayas_jobs: 40, himalayas_status_checks: 5
  }
}' | curl --fail-with-body "$INGESTION_API/sources" \
  -H "Authorization: Bearer $RW_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' --data-binary @-
```

4. Keep the returned UUID as `SOURCE_ID`. Set optional `HIMALAYAS_API_KEY`
   in the worker environment and restart the worker to load it. The key is
   sent only to the scoped Himalayas API endpoints as a bearer header.

```sh
PYTHONPATH=services/api:workers uv run celery -A ingestion.celery_app:app worker -Q ingestion --concurrency=4 --loglevel=INFO
PYTHONPATH=services/api:workers uv run celery -A ingestion.celery_app:app beat --loglevel=INFO --schedule /tmp/recruitment-celerybeat
```

5. Enable and queue the first due poll. The manual queue command is optional
   when Beat is running.

```sh
curl --fail-with-body -X PATCH "$INGESTION_API/sources/$SOURCE_ID" \
  -H "Authorization: Bearer $RW_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' --data '{"enabled":true}'

PYTHONPATH=services/api:workers uv run python -m ingestion.cli "$SOURCE_ID"

curl --fail-with-body "$INGESTION_API/runs?source_id=$SOURCE_ID" \
  -H "Authorization: Bearer $RW_ADMIN_TOKEN"
curl --fail-with-body "$INGESTION_API/candidates?source_id=$SOURCE_ID" \
  -H "Authorization: Bearer $RW_ADMIN_TOKEN"
```

## Review and publish

Choose a current pending candidate. Check the employer, India eligibility
and timezone, original listing, and unmodified Apply URL against the provider.
Set `ITEM_ID`, `JOB_ID`, `VERSION`, and your actual `REVIEW_REASON`.

```sh
jq -n --argjson version "$VERSION" --arg reason "$REVIEW_REASON" \
  '{action:"accept",version:$version,reason:$reason}' |
curl --fail-with-body "$INGESTION_API/candidates/$ITEM_ID/review" \
  -H "Authorization: Bearer $RW_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' --data-binary @-
```

Set `APPROVED_VERSION` to the version in the acceptance response, then publish.

```sh
jq -n --argjson version "$APPROVED_VERSION" --arg reason "$REVIEW_REASON" \
  '{action:"publish",version:$version,reason:$reason}' |
curl --fail-with-body "http://127.0.0.1:8000/api/v1/admin/opportunities/$JOB_ID/transitions" \
  -H "Authorization: Bearer $RW_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' --data-binary @-
```

Open `http://127.0.0.1:3000/jobs/$JOB_ID` and confirm the checked Apply URL,
linked credit and visibility on Corporate Jobs and Search.

## Poll and closure behaviour

Browse uses the opaque `nextCursor` inside each bounded poll. With a budget
of at least 40, one India Search page can use 20 of the configured job slots.
Set `himalayas_india_search: false` to give the entire budget to Browse.
Daily polls start at the most recent page and upsert by provider GUID. There
is no full-catalogue mirror or cross-run browse cursor. A separate bounded
rotation checks already-published records. A per-job HTTP 410 closes the
record. A current status payload with explicit India exclusion removes the
listing. HTTP 404, failed requests and absence from partial results have no
closure effect. Confirmed closures and known expiries are removed from public
reads, with internal audit history retained.

## Verification

Anonymous Browse, India Search and per-job status reads returned HTTP 200.
A bounded adapter probe fetched 40 records, identified 20 India-eligible
records and excluded 20. The status response matched the requested GUID.
The live reads staged and published zero jobs.

An isolated fixture passed the Beat, worker, review, publication and browser
flow, including homepage, Corporate Jobs, Search and detail visibility.
Chrome checked the linked source credit, exact Apply URL and absence of
JobPosting markup. The full PostgreSQL backend suite passed 28 tests and
the frontend suite passed 10. Ruff, Prettier, ESLint, TypeScript, the
production build and Alembic drift checks passed.
