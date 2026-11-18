# Architecture

Recruitment Waala is a modular monorepo with one domain backend and one shared
PostgreSQL database. The Celery process handles eventual asynchronous work alongside
the API. Redis is the queue broker. Next.js owns presentation and calls the API
over HTTP as product routes are introduced.

```mermaid
flowchart LR
    Browser --> Web["Next.js"]
    Monitor --> API["FastAPI /health"]
    Web -. product reads .-> API
    API -. product transactions .-> PG[("PostgreSQL")]
    Alembic --> PG
    Worker["Celery worker"] <--> Redis[("Redis broker")]
    Worker -. ingestion transactions .-> PG
    Worker -. approved fetches .-> Sources["Approved sources"]
```

Solid arrows show Phase 0 interfaces; the worker is started explicitly. Dotted
arrows show planned integrations. Web health checks rendering and API health checks
process liveness. Add dependency-aware readiness before routing production traffic.

| Location | Ownership |
| --- | --- |
| `apps/web` | App Router, TypeScript, Tailwind v4, shadcn/ui configuration |
| `services/api` | FastAPI, SQLAlchemy metadata, migrations and API tests |
| `workers/ingestion` | Celery entry point and future ingestion orchestration |
| `packages/contracts` | Shared API specifications and future generated clients |
| `infra` | Infrastructure guidance and future deployment definitions |
| `docs` | Product scope, schemas, API and operations policy |

## Domain boundaries

The catalogue owns public records and lifecycle. Government recruitment and exam
artifacts share a cycle with explicit parent links. Corporate roles and internships
use the same catalogue with category validation. Search initially queries published
PostgreSQL projections with indexed filters, then evaluates full-text indexes from
observed query plans. Accounts own profiles and saves, and alerts own subscriptions
and future delivery state. Ingestion owns source observations, while moderation owns
approval decisions and transactional catalogue updates.

```mermaid
flowchart TD
    Approval["Approve permission and register source"] --> Poll["Fetch within source limits"]
    Poll --> Observe["Record run and observations"]
    Observe --> Match["Resolve organisation, cycle and opportunity"]
    Match --> Review["Review evidence and changes"]
    Review -->|Approve| Commit["Commit catalogue and history together"]
    Review -->|Reject or request changes| Hold["Keep review evidence"]
    Commit --> Read["Refresh discovery and evaluate opted-in alerts"]
```

The ingestion diagram describes the planned workflow. Lock or compare the current
record inside the publishing transaction. Use durable operation keys and an outbox
when alert deliveries or queue publishes must follow database writes. Redis messages
can be redelivered, so workers need idempotency and bounded retries.

Use private database and broker networking in production, scoped service identities,
TLS, externally managed secrets and explicit origin policy. Separate runtime,
migration and operator privileges. Disable verbose errors and redact credentials and
personal data from logs. Plan backups and restore drills, structured logs with
request/run IDs, queue lag metrics and stale-source alerts before launch.

## Phase 2 runtime

Next.js reads the catalogue over server-to-server HTTP and sends URL filter
state to FastAPI. Public data is fetched per request so withdrawals and source
disabling take effect without waiting for a frontend build. Production fetch
errors surface through the existing route error boundary. The development-only
demo can still run with the Phase 1 local search.

Phase 2 uses the existing discovery index and joined, parameterised PostgreSQL
queries. The initial substring search favours reference and short-token matching.
Measure query plans before adding trigram or full-text indexes for larger
catalogues. Configure request limits at the private ingress before internet
exposure. User identity, per-reviewer attribution and automated workers remain
separate from the public read path.

## Phase 3 runtime

Beat dispatches due, approved sources to Celery. A PostgreSQL advisory lock
serialises polling per source. Ingestion records observations, drafts and review
candidates in the same database used by FastAPI. The frontend continues to
read the existing public routes without a data-cache delay. See the
[ingestion architecture](INGESTION_ARCHITECTURE.md) for the publication boundary.
