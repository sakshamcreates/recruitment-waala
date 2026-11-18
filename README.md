# Recruitment Waala

**Every Opportunity. One Platform.**

Phase 1 adds an illustrative discovery experience for Indian government jobs, corporate roles, internships and exam updates. The Next.js web app and FastAPI also expose health endpoints. PostgreSQL holds an empty
catalogue and provenance schema. Celery is configured for a dedicated ingestion
queue with no registered ingestion tasks or schedules.

## Frontend preview

Run `npm ci` and `npm run dev -w @recruitment/web`, then visit
`http://127.0.0.1:3000`. The frontend reads local typed fixtures through its
catalogue repository and runs independently of Docker or FastAPI.

- Browse the seven category routes, search at `/search` and open an example at
  `/jobs/<id>`. Search terms, filters, sort and page are stored in the URL.
- `/dashboard` and `/admin` show read-only demonstrations.
- The catalogue uses fictional issuers, references and dates. The deadline
  filter uses 18 November 2026 as the sample date. Applications, source links,
  accounts, and administrative actions are unavailable.
- All preview pages carry noindex metadata. An optional build-time
  `SITE_ORIGIN` sets the HTTPS canonical base for the homepage, category and
  search routes. A published-only sitemap belongs with the verified catalogue.

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
uv run uvicorn recruitment_api.main:app --app-dir services/api --reload
npm run dev -w @recruitment/web
PYTHONPATH=workers uv run celery -A ingestion.celery_app:app worker --loglevel=INFO
```

The worker is optional for health checks. Inspect the local endpoints with:

```sh
curl --fail --silent http://127.0.0.1:8000/health
curl --fail --silent http://127.0.0.1:8000/openapi.json
curl --fail --silent http://127.0.0.1:3000/health
```

The API returns `{"status":"ok"}`, and the frontend shows a web status message.
Both are liveness checks. Use `docker compose ps` for dependency health. Use
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
