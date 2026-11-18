# API specification

## Phase 0 interfaces

| Method and path | Response |
| --- | --- |
| `GET /health` | HTTP 200 with `{"status":"ok"}` when the API process is serving. |
| `GET /openapi.json` | FastAPI-generated OpenAPI document for implemented operations. |
| Web `GET /health` | HTTP 200 with a minimal HTML page verifying the web app renders. |

The health endpoints make no dependency calls. A future private readiness endpoint
will verify required dependencies with short timeouts.

## Proposed v1 operations

All routes in this table are planned. Paths are relative to `/api/v1`.

| Method and path | Access | Contract |
| --- | --- | --- |
| `GET /opportunities` | Public | Filter by query, category, organisation, geography and status. Published, unexpired listings are the default. |
| `GET /opportunities/{id}` | Public | Return published or formerly public opportunity with category-specific detail and official attribution. |
| `GET /opportunities/{id}/history` | Public | Cursor-paginated, redacted material changes. |
| `GET /me`, `PATCH /me/profile` | Member | Read the current user and update allowed profile fields. |
| `GET /me/saved-jobs` | Member | Paginate the current member's saves. |
| `PUT /me/saved-jobs/{id}`, `DELETE /me/saved-jobs/{id}` | Member | Idempotent save and remove. |
| `GET /me/alerts`, `POST /me/alerts` | Member | List subscriptions or create a filter and cadence subscription. |
| `PATCH /me/alerts/{id}`, `DELETE /me/alerts/{id}` | Owner | Update, disable or remove a subscription. |
| `GET /admin/reviews`, `POST /admin/opportunities/{id}/reviews` | Moderator | List queue or submit a decision, rationale and expected version. |
| `GET /admin/sources`, `GET /admin/ingestion-runs` | Admin | Inspect permission configuration and sanitized ingestion outcomes. |
| `POST /admin/sources/{id}/runs` | Admin | Request a run for an enabled source using an idempotency key. Reply 202 with a run reference. |

Public list envelopes contain `items` and `next_cursor`. Cursor tokens are opaque
and bound to normalized filters and a stable sort. Default to 20 items and cap
pages at 100. Use UUID identifiers, RFC 3339 timestamps and discriminated category
payloads. Public attribution includes issuer, official URL and verification time.

Use an external identity provider. Validate token issuer, audience and expiration,
then enforce ownership or role per operation. Reject unsupported fields and bound
input sizes. Return consistent problem details with a request ID and field errors
where applicable. Use 401 for missing or invalid identity, 403 for insufficient
role, 404 for unavailable resources, 409 for conflicting writes, 422 for validation
and 429 with Retry-After when throttled. Document additive compatibility and
review breaking changes under a new major API version.
