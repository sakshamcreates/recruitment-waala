# Source registry and source evaluation

The protected ingestion API operates under the existing Phase 2 internal
service credential. A source identifies one issuer or employer, one endpoint,
one adapter, and three independent scopes for retrieval, notice links and
application links. Every scope is a list of absolute HTTPS host and path
prefixes. Source terms and an approval reference are mandatory. Record the
operator, permission scope, terms revision, redistribution rights, expiry,
rate limits and retention in your approval record. Keep secrets out of the
registry and include only an opaque reference to restricted evidence.

Registration defaults to disabled. The service makes no external requests
during registration or validation. An operator explicitly enables the source
after reviewing its permission record. Disabling it stops future polling
and removes its records from public reads. Disable before changing approval
or retrieval scope. Reconfiguration invalidates observations made under the
old approval and requires fresh editorial review before records reappear.

| Candidate | Official source or documentation | Status |
| --- | --- | --- |
| Staff Selection Commission | [SSC](https://ssc.gov.in/) publishes notices and exam material. | No approved recruitment feed or automated access permission was established. Generic HTML and PDF support is available for a permitted scope. |
| Union Public Service Commission | [UPSC website policies](https://cms.upsc.gov.in/website-policies/) describe attribution and permission for reproduction. | Linking allowances do not establish an ingestion and republication grant. Awaiting permission. |
| Railway Recruitment Boards | [RRB Chandigarh official notice](https://www.rrbcdg.gov.in/uploads/2025/04-SCTRL/CEN042024-SectionController.pdf) identifies official RRB notices and corrigenda. | No approved board feed or cross-board retrieval grant was established. Review each board and scope independently. |
| Tamil Nadu Public Service Commission | [TNPSC recruitment](https://www.tnpsc.gov.in/english/recruitments.html) and [web policy](https://www.tnpsc.gov.in/english/privacy_policy.html). | The web policy requires permission for reproduction and linking. Awaiting permission. |
| Other official boards | Issuer-specific authorised feed or scoped official notice. | No issuer permission recorded. |
| Greenhouse | [Job Board API](https://docs.greenhouse.io/job-board.html) documents public GET endpoints. | Single-board adapter fixture-tested. Employer approval and applicable provider terms must be recorded for the exact board. No live board enabled. |
| Lever | [Postings API](https://github.com/lever/postings-api) and [developer FAQ](https://hire.lever.co/developer/support). | Single employer postings adapter fixture-tested. The public postings API serves published postings. Employer and provider permission for this use remains a deployment prerequisite. |
| Sarkari Result | Potential secondary discovery source only. | No authorised feed, documented integration permission, or dedicated adapter. |
| Custom JSON | Authorised endpoint returning a JSON list of canonical records. | Fixture-tested. Endpoint-specific permission, schema agreement and completeness evidence required. |

Documentation review did not involve live recruitment ingestion. Public
access to documentation or a GET endpoint establishes technical capability.
Evaluate and record redistribution and automated retrieval rights separately.

Provider terms references reviewed alongside the API documentation include
the [Greenhouse legal center](https://www.greenhouse.com/de/legal) and
[Lever terms of service](https://www.lever.co/legal/terms-of-service).
A board-specific agreement and authorisation remain necessary for this deployment.
