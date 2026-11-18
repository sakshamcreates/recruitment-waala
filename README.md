# Recruitment Waala

**Every Opportunity. One Platform.**

Recruitment Waala combines Indian government recruitment, corporate roles,
internships and exam notices. Phase 2 serves the existing Next.js frontend from
the PostgreSQL catalogue through FastAPI. Celery and Beat poll due sources with recorded approval.

## Phase 2 catalogue

The web app reads the FastAPI public catalogue by default. Set
`CATALOGUE_API_ORIGIN=http://127.0.0.1:8000` in `apps/web/.env.local` or the
server environment. An empty migrated database produces an empty public
catalogue. A backend failure produces an error state.

For a frontend-only demonstration, run
`CATALOGUE_MODE=demo npm run dev -w @recruitment/web`. This explicit mode uses
fictional fixtures and example dates. Production builds always use FastAPI
for catalogue reads. The dashboard and moderation routes remain demonstration UI.

The [API specification](docs/API_SPEC.md) documents endpoint examples, the
protected editorial workflow, token rotation and manual source evidence.

## Full monorepo prerequisites

- Node.js 24 and npm
- Python 3.13 and [uv](https://docs.astral.sh/uv/)
- Docker with the Compose v2 plugin
- OpenSSL for the example local credential generation

## Set up

Run these commands from the workspace root.

```sh
npm ci
uv sync --locked
cp .env.example .env
```

Set `POSTGRES_PASSWORD` in `.env` to a fresh local-only value. Generate one with
`openssl rand -hex 24`. Set `DATABASE_URL` to
`postgresql+psycopg://recruitment:<password>@127.0.0.1:5432/recruitment` using
the same password. URL-encode it if you use a value with reserved characters.
The PostgreSQL image uses this password on first initialization of its volume.
Keep `.env` private. An existing shell value takes precedence for the Python
commands and Compose interpolation.

```sh
docker compose config --quiet
docker compose up -d --wait
uv run alembic upgrade head
```

## Run

Start each process in a separate terminal from the workspace root.

```sh
uv run uvicorn recruitment_api.main:app --app-dir services/api --no-access-log --reload
npm run dev -w @recruitment/web
PYTHONPATH=services/api:workers uv run celery -A ingestion.celery_app:app worker --loglevel=INFO
```

The worker is optional for health checks. Inspect the local endpoints with:

```sh
curl --fail --silent http://127.0.0.1:8000/health
curl --fail --silent http://127.0.0.1:8000/ready
curl --fail --silent http://127.0.0.1:8000/api/v1/opportunities
curl --fail --silent http://127.0.0.1:8000/openapi.json
curl --fail --silent http://127.0.0.1:3000/health
```

The API returns `{"status":"ok"}`, and the frontend shows a web status message.
The health endpoints are liveness checks. API readiness also checks the database. Use `docker compose ps` for dependency health. Use
`docker compose down` to stop local services and retain volumes.

## Test and format

```sh
npm run format:check
npm run lint
npm run typecheck
npm test -w @recruitment/web
npm run build
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run alembic check
```

Format changed code with `npm exec -- prettier --write apps/web package.json`
and `uv run ruff format .`. The CI workflow runs the web and backend checks and
exercises Compose and migration upgrade, drift check, downgrade and re-upgrade
against an ephemeral database. Schema authors can use
`uv run alembic revision --autogenerate -m "describe change"` against an upgraded
development database. Review generated revisions before committing them.
Downgrading to base removes the application schema and its data, so use a
disposable database for that check.

## Design documents

- [Product requirements](docs/PRODUCT_REQUIREMENTS.md)
- [Architecture and diagrams](docs/ARCHITECTURE.md)
- [Database schema and relationships](docs/DATABASE_SCHEMA.md)
- [API specification](docs/API_SPEC.md)
- [Source and verification policy](docs/SOURCE_POLICY.md)
- [Phase roadmap](docs/PHASE_ROADMAP.md)

## PostgreSQL integration test and optional demo seed

Point `TEST_DATABASE_URL` at a migrated disposable PostgreSQL database and
run `uv run pytest`. The integration test rolls back its own records. CI runs
this check with the ephemeral Compose database.

For a persistent editorial sample, create a separate PostgreSQL database whose
name ends in `_demo`, point `DATABASE_URL` at it, then run:

```sh
uv run alembic upgrade head
RW_ENV=development PYTHONPATH=services/api uv run python -m recruitment_api.seed_demo
```

The sample is a fictional draft with no external links. It remains outside all
public responses. For the Phase 3 ingestion handoff, adapter-produced data should
enter through `source_registry`, `ingestion_runs` and `source_items`. Keep
observations separate from moderation and publication. See the
[source policy](docs/SOURCE_POLICY.md) and [roadmap](docs/PHASE_ROADMAP.md) for
permission gates and sequencing.

## Phase 3 worker and scheduling

Phase 3 adds an approval-gated ingestion worker and scheduler. See
[operations](docs/INGESTION_OPERATIONS.md) to start Beat and the worker,
[the source registry](docs/SOURCE_REGISTRY.md) for onboarding decisions, and
[verification](docs/PHASE_3_VERIFICATION.md) for local tests. Existing
installations must run `uv run alembic upgrade head` before running Phase 3.
