# Phase 3 verification

The reproducible tests use development-only deterministic input. No external
source registry rows are seeded by Alembic, the worker, or the test suite in
a production database. Integration tests create and remove their own
PostgreSQL schema.

```sh
uv sync --locked
uv run alembic upgrade head
uv run alembic check
TEST_DATABASE_URL="$DATABASE_URL" uv run pytest
uv run ruff check .
uv run ruff format --check .
npm run format:check
npm test -w @recruitment/web
npm run lint
npm run typecheck
npm run build
```

The test suite covers scoped ATS and government adapters, valid and malformed
PDF, private DNS denial, scheduling and retries, concurrent source polls,
deduplication, separate cycles, review, publication, corrected deadline and
vacancy count, incomplete snapshots, suspected absence, withdrawal, timeout,
health telemetry and public visibility. Live recruitment retrieval is gated
on recorded approval for a particular source. Refer to the
[source evaluation](SOURCE_REGISTRY.md) for the current onboarding status.

## Executed verification

- PostgreSQL-backed pytest suite passed 16 tests. It includes a policy test
  showing that an unreviewed ATS draft stays private and that an accepted draft
  only releases under an explicit source opt-in.
- A disposable database passed upgrade, downgrade to `0002`, re-upgrade and
  Alembic metadata drift checks.
- A local process smoke test used Redis, Celery Beat, a worker, FastAPI and a
  production Next.js build. The worker transport supplied deterministic bytes
  without external HTTP. The test confirmed an empty public catalogue before
  review, then reviewed and published the fixture and opened it in Chrome.
- Nine frontend tests, TypeScript checking, ESLint, Prettier, and the production
  build passed. Ruff lint and formatting passed. The Python dependency audit
  reported zero known findings at verification time.

Live external verification remains pending documented permission for an exact
board or endpoint. The deterministic smoke used a local test harness outside
the application and removed its database afterward.
