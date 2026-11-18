# Ingestion operations

Start the database, API and web app as described in the README, then run the
worker and Beat in separate processes from the workspace root:

```sh
PYTHONPATH=services/api:workers uv run celery -A ingestion.celery_app:app worker -Q ingestion --concurrency=4 --loglevel=INFO
PYTHONPATH=services/api:workers uv run celery -A ingestion.celery_app:app beat --loglevel=INFO --schedule /tmp/recruitment-celerybeat
```

Run a single Beat instance. Use a private Redis service with authentication
and TLS in production. Run the worker with a prefork pool for Celery time
limits and configure network egress controls, CPU limits and memory limits
for the worker container. The PDF child additionally has a wall-clock
timeout, a CPU limit, and a Linux address-space limit.

## Register and enable

Use an authorised infrastructure instance and export the Phase 2 internal
token in the operator shell. Create the issuer first with the restricted
database role. Fill the actual issuer UUID, scoped endpoint, approval reference,
terms and scope prefixes in `source.json`. Fields are documented in OpenAPI
under `SourceInput` and `PollConfig`.

```sh
curl --fail-with-body http://127.0.0.1:8000/api/v1/admin/ingestion/sources \
  -H "Authorization: Bearer $RW_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' --data-binary @source.json

curl --fail-with-body -X PATCH "http://127.0.0.1:8000/api/v1/admin/ingestion/sources/$SOURCE_ID" \
  -H "Authorization: Bearer $RW_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' --data '{"enabled":true}'
```

The polling interval must be at least five minutes. Use a longer interval
and per-request gap whenever approval terms require them. The worker checks
robots rules for government HTML and PDF and fails closed when it cannot
retrieve or use the rules. No redirects are followed. Prefer authorised JSON
when the operator can document feed terms and coverage.

## Collect and review

```sh
PYTHONPATH=services/api:workers uv run python -m ingestion.cli "$SOURCE_ID"

curl --fail-with-body "http://127.0.0.1:8000/api/v1/admin/ingestion/runs?source_id=$SOURCE_ID" \
  -H "Authorization: Bearer $RW_ADMIN_TOKEN"

curl --fail-with-body "http://127.0.0.1:8000/api/v1/admin/ingestion/candidates?source_id=$SOURCE_ID" \
  -H "Authorization: Bearer $RW_ADMIN_TOKEN"
```

The manual command enqueues the same task as Beat and respects the next
permitted poll time. Compare the latest candidate with the issuing notice.
Post `action` (`accept` or `reject`), `version` and `reason` to
`/api/v1/admin/ingestion/candidates/{item_id}/review`. Acceptance of a draft
marks it approved. Publish through the existing Phase 2 transition with the
returned version. For a Greenhouse or Lever source with explicit permission
for scheduled release, `publication_policy: release_reviewed_ats` lets Beat
release an eligible corporate draft after acceptance. The manual default
continues to require an explicit publish transition. Acceptance of a published
correction or withdrawal makes
that reviewed change visible immediately. For invalid extraction, review the
notice manually and use the Phase 2 draft and evidence workflow. A submitted
draft with incorrect fields must be rejected before it can be edited.

## Failures and recovery

Inspect source health, last run and error code before retrying. Timeouts and
retryable HTTP errors use capped worker retries, exponential delay with
jitter, and Retry-After when present. A lost worker leaves a bounded lease.
The next eligible run marks abandoned poll rows failed. Failed runs never
infer closures. Partial or duplicate snapshots also leave absence decisions
alone. For repeated parser failures, disable the source, review permission
and fix the adapter against captured or synthetic fixtures. Reconfigure the
source while disabled and explicitly enable it after review.

The worker accepts only HTTPS public addresses, pins the validated address
for TLS, limits response sizes, rejects compression and never follows redirects.
Keep infrastructure-level egress restriction in place as defense in depth.
Registry configuration must contain no credentials. Revoke or disable a
source promptly when terms change. Define observation and audit retention
before enabling a source. No scheduled data deletion is configured here.
