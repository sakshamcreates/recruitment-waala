# Phase roadmap

| Phase | Scope | Exit gate |
| --- | --- | --- |
| 0 · Foundation | Requirements, architecture, schema, API and source policy. Minimal apps, local services, migrations, worker entry point and CI. | Apps and checks run, schema is empty and reversible, source registry has no entries. |
| 1 · Frontend preview | Search and category pages, opportunity details, and read-only dashboard and moderation previews using illustrative fixtures. | Discovery and filters are usable on desktop and mobile. Fixtures have clear provenance and no application links. |
| 2 · Verified catalogue integration | Connect public reads to FastAPI and introduce a verified editorial catalogue. Add live category validation, expiry and correction history. | Issuer evidence and cycle identity drive publication. Official attribution and permissions are reviewed for each category. |
| 3 · Accounts and alerts | Identity, profile, saves, opt-in subscriptions and delivery observability. | Authorisation, deletion, idempotent delivery and unsubscribe validated. |
| 4 · Approved automation | Pilot adapters, throttling, ingestion controls and source monitoring. | Permissions recorded, recovery exercised and false merges measured before wider rollout. |

Phase 0 and the Phase 1 frontend preview are implemented. Later phases depend on source permission, an identity
provider decision, privacy and retention review, and production readiness checks.
