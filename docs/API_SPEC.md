# API specification

FastAPI serves its machine-readable contract at `/openapi.json`. `GET /health`
checks process liveness. `GET /ready` checks that PostgreSQL and the publication
migration are available. Web health is served separately at `/health`.

## Public catalogue

| Method and path | Contract |
| --- | --- |
| `GET /api/v1/opportunities` | Active, approved, unexpired catalogue with `items`, `total`, `page`, `limit`, `facets` and `next_cursor`. |
| `GET /api/v1/opportunities/{id}` | UUID detail. Previously published expired and withdrawn records remain available while provenance is enabled. |
| `GET /api/v1/opportunities/{id}/history` | Most recent redacted publication and withdrawal events, with optional `limit`. |
| `GET /api/v1/changes` | Recent public publication and withdrawal events across visible records. |
| `GET /api/v1/organisations` | Organisations represented in active results, ordered by name and UUID, with `page` and `limit`. |
| `GET /api/v1/categories` | Supported category identifiers. |

List filters are `q`, `category`, `state`, `qualification`, `organisation`
(name), `experience`, `type` (employment or internship compensation), `mode`,
`duration`, and `deadline` (seven days via `week` or 30 days via `month`).
Keywords match literal case-insensitive substrings across title, issuer and
metadata. All tokens and selected filters must match. Sort with `newest`,
`title`, or `deadline`; each order includes a UUID tie-break. Numbered pages
match the Phase 1 URL contract and cap page size at 100. Inserts, withdrawals and expiry between requests can shift numbered pages.
Clients can pass `next_cursor` as `cursor` with the same filters, sort and limit
and omit `page`. This keyset continuation uses the last sort tuple.

```sh
curl 'http://127.0.0.1:8000/api/v1/opportunities?category=government_job&qualification=Graduate&sort=deadline&limit=5'
curl 'http://127.0.0.1:8000/api/v1/organisations?limit=10'
curl 'http://127.0.0.1:8000/api/v1/changes'
```

Deadline and publication values are RFC 3339 timestamps. Unavailable fields are
null. List facets are category-scoped before other filters and capped at 100
values per field. Opportunity details use a discriminated `details.category`
payload. Provenance includes the source slug, source observation time, recorded
editorial verification time, and official URL when still valid.

## Internal editorial workflow

All routes below require an internal bearer credential and are disabled under
`RW_ENV=production` or when the environment is absent. Use a private
development or infrastructure deployment with `RW_ADMIN_ENABLED=true` and
`RW_ADMIN_TOKEN` of at least 32 ASCII characters. An optional
`RW_ADMIN_PREVIOUS_TOKEN` allows a bounded rotation overlap. Restart the service
when injecting new secret environment values, then remove the previous value
after callers rotate. Keep these values out of browser variables and access
logs. Route this internal service behind private networking and TLS. Proper
role-based identity and attributable reviewers are future work.

| Method and path | Contract |
| --- | --- |
| `POST /api/v1/admin/opportunities` | Create a draft for a preprovisioned organisation. Returns UUID and version. |
| `PUT /api/v1/admin/opportunities/{id}` | Replace editable draft fields with the expected `version`. Rejected drafts can be corrected and resubmitted. |
| `POST /api/v1/admin/opportunities/{id}/transitions` | Accepts `version`, `action`, and `reason`, plus a `source_item_id` for approval. |

The sequence is create, submit, approve, publish, then optionally withdraw.
A submitted record can be rejected. Every successful mutation returns the
next version. Replays with an old version conflict, and duplicate canonical
creates return 409. Reviewer decisions and state changes are committed together.

Before creating a draft, an operator provisions the issuer and its approved
source in `organisations` and `source_registry` using a restricted database
role. After creation, record the evidence with an explicitly manual
`ingestion_runs` entry and a linked `source_items` observation containing the
draft UUID, exact notice URL, observation date and SHA-256 of the reviewed
content. The approved source must belong to the organisation. Approval records
the operator's manual verification attestation after these checks. URLs must
use HTTPS on the exact approved source hostname. An optional application URL
must share that hostname. Publication rechecks the evidence and deadline.
Disabling the source removes its records from the public catalogue.

Errors include `status`, `detail`, and `request_id`. Invalid input returns
422, stale versions and invalid transitions return 409, and database failures
return 503. Requests are logged by route template and status. Cross-origin
browser access is disabled by default. Next.js uses server-to-server requests.

For a draft against a provisioned issuer, put the existing organisation UUID,
cycle and opportunity keys, title, and category details into a local JSON
file. For example, `details` can contain only `category: government_job` when
no additional fields are known. Run the following against the private
development or infrastructure API with the token exported locally:

```sh
curl --fail-with-body -X POST http://127.0.0.1:8000/api/v1/admin/opportunities \
  -H "Authorization: Bearer $RW_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' --data-binary @draft.json
```

Use the returned UUID and version to submit. Approve only after supplying a
manually verified observation ID. Use a migration role for DDL, a restricted
operator role for source provisioning, and a read-only database role for
public API deployments. The development Compose role owns its local schema.

## Phase 3 protected ingestion

Under `/api/v1/admin/ingestion`, the existing internal credential protects:

- `POST /sources` to register a scoped source.
- `PATCH /sources/{id}` to enable or disable it.
- `PUT /sources/{id}/config` to renew permission or change scope while disabled.
- `GET /sources`, `GET /runs`, and `GET /candidates` for bounded monitoring and review.
- `POST /candidates/{item_id}/review` for versioned acceptance or rejection.

Managed sources use explicit notice and application URL scopes. Legacy sources
retain the Phase 2 single-host check. Public history also includes reviewed
`correction` events. Existing public routes and envelopes remain in place.
