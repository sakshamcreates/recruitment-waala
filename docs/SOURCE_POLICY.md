# Source and verification policy

Start with an empty source registry. Enable a source only after an owner documents
the organisation, permitted use and redistribution, allowed endpoint and redirect
hosts, approved access method, rate allowance, attribution, retention, and a
permission reference and review date. Pause during permission disputes or on
material terms changes. Keep credentials in a secret manager or local environment.

| Adapter type | Admission and verification |
| --- | --- |
| Approved API | Check the provider terms and use only approved endpoints. Greenhouse and Lever employer job-board APIs are candidates subject to terms and permission. Confirm the board belongs to the employer. |
| Authorised feed | Document the agreement, format, permitted fields, attribution and how changes and withdrawals are signaled. |
| Permitted official page | Require documented permission and applicable robots rules. Restrict collection to approved pages and verify government opportunities against the issuing body. |

Sarkari Result is not assumed to offer a public API. Do not ingest it without
documented authorization. Secondary references can help an operator locate primary
evidence. Before publishing a government record, confirm the issuing authority,
official URL, notification reference, cycle and dates against official evidence.
Hold ambiguous matches and conflicting dates for human verification. Check official
corrigenda and withdrawal notices against the same cycle.

## Future adapter interface

An approved adapter takes source configuration and a checkpoint, fetches a bounded
page and returns observations with source URL, external key, observed timestamp,
content hash, canonical hints and next checkpoint. The runner owns network
controls, run recording, checkpoint commits, retries and metrics. The normalizer
validates category payloads. Moderation owns publication.

Allowlist HTTPS destinations and revalidate redirects and resolved addresses.
Block private, loopback and link-local network destinations. Limit download size,
timeouts and concurrency. Identify the collector as agreed, honor Retry-After and
stop when authorization fails or CAPTCHA appears. Avoid bypass mechanisms and
unapproved scraping. Treat external payloads and documents as untrusted, restrict
stored snapshots to authorized staff and avoid candidate-level data. Preserve
permission evidence, sanitized run outcomes and material corrections.
