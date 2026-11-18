import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from recruitment_api import schema
from recruitment_api.catalogue import get_session
from recruitment_api.contracts import https_origin
from recruitment_api.main import app
from recruitment_api.models import Details, Job
from sqlalchemy import create_engine, func, insert, update
from sqlalchemy.orm import Session


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.parametrize(
    "url",
    [
        "http://www.upsconline.nic.in",
        "https://127.0.0.1/a",
        "https://localhost/a",
        "https://user@www.upsconline.nic.in/a",
        "https://www.upsconline.nic.in\\@other.com",
        "https://example.invalid/path",
    ],
)
def test_invalid_url(url):
    with pytest.raises(ValueError):
        https_origin(url)


@pytest.mark.anyio
async def test_validation_and_production_deny(monkeypatch):
    monkeypatch.setenv("RW_ENV", "production")
    monkeypatch.setenv("RW_ADMIN_ENABLED", "true")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/api/v1/admin/opportunities", json={})).status_code == 404
        assert len((await client.get("/api/v1/categories")).json()) == 7


@pytest.mark.anyio
async def test_postgresql_catalogue(monkeypatch):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated disposable PostgreSQL database.")
    engine = create_engine(url)
    monkeypatch.setenv("RW_ENV", "development")
    monkeypatch.setenv("RW_ADMIN_ENABLED", "true")
    token = uuid4().hex
    monkeypatch.setenv("RW_ADMIN_PREVIOUS_TOKEN", token)
    monkeypatch.setenv("RW_ADMIN_TOKEN", uuid4().hex)
    editor = {"Authorization": f"Bearer {token}"}
    root = "/api/v1"
    admin = f"{root}/admin/opportunities"
    origin = "https://www.upsc.gov.in"
    notice = f"{origin}/"
    with engine.connect() as connection, connection.begin() as transaction:

        def session():
            with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
                yield db

        app.dependency_overrides[get_session] = session
        try:

            def add(table, **values):
                return connection.scalar(insert(table).values(**values).returning(table.c.id))

            # All records are isolated in a transaction that is rolled back.
            org = add(schema.organisations, slug="integration-test", name="Test Issuer")
            source = add(
                schema.source_registry,
                slug="integration-test",
                organisation_id=org,
                adapter_kind="official_page",
                endpoint_url=origin,
                enabled=True,
                approved_at="2026-01-01T00:00:00Z",
                permission_reference="test only",
            )
            run = add(schema.ingestion_runs, source_id=source, run_key="manual-test")
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
                assert (await api.get(f"{root}/opportunities?limit=0")).status_code == 422
                assert (await api.get(f"{root}/opportunities?unknown=x")).status_code == 422
                assert (await api.post(admin, json={})).status_code == 401
                draft = dict(
                    organisation_id=str(org),
                    cycle_key="cycle-a",
                    opportunity_key="test",
                    title="Test Record",
                    official_url=notice,
                    details=dict(
                        category="government_job",
                        reference="REF/001",
                        qualification="Graduate",
                        state="Delhi",
                    ),
                )
                bad = {**draft, "apply_url": "javascript:alert(1)"}
                assert (await api.post(admin, json=bad, headers=editor)).status_code == 422

                async def publish(cycle):
                    body = {**draft, "cycle_key": cycle}
                    response = await api.post(admin, json=body, headers=editor)
                    assert response.status_code == 201, response.text
                    job_id = response.json()["id"]
                    assert (await api.get(f"{root}/opportunities/{job_id}")).status_code == 404
                    duplicate = await api.post(admin, json=body, headers=editor)
                    assert duplicate.status_code == 409, duplicate.text
                    check = await api.put(
                        f"{admin}/{job_id}",
                        json={**body, "version": 1},
                        headers=editor,
                    )
                    assert check.status_code == 200, check.text
                    version = 2
                    path = f"{admin}/{job_id}/transitions"
                    invalid = await api.post(
                        path,
                        json=dict(version=version, action="publish", reason="test"),
                        headers=editor,
                    )
                    assert invalid.status_code == 409
                    observation = add(
                        schema.source_items,
                        job_id=job_id,
                        source_id=source,
                        run_id=run,
                        external_key=cycle,
                        content_sha256="a" * 64,
                        source_url=notice,
                    )
                    for action in ("submit", "approve", "publish"):
                        payload = dict(version=version, action=action, reason="test")
                        if action == "approve":
                            payload["source_item_id"] = str(observation)
                        response = await api.post(path, json=payload, headers=editor)
                        assert response.status_code == 200, response.text
                        version += 1
                    return job_id, version

                rejected = await api.post(
                    admin,
                    json={**draft, "cycle_key": "rejected"},
                    headers=editor,
                )
                assert rejected.status_code == 201
                rejected_id = rejected.json()["id"]
                rejected_path = f"{admin}/{rejected_id}/transitions"
                for version, action in enumerate(("submit", "reject"), start=1):
                    response = await api.post(
                        rejected_path,
                        json=dict(version=version, action=action, reason="test"),
                        headers=editor,
                    )
                    assert response.status_code == 200
                assert (await api.get(f"{root}/opportunities/{rejected_id}")).status_code == 404
                first, version = await publish("cycle-a")
                second, _ = await publish("cycle-b")
                row = await api.get(f"{root}/opportunities/{first}")
                assert row.json()["provenance"]["verified_at"]
                with Session(bind=connection) as db:
                    assert db.get(Job, first).status == "published"
                    assert db.get(Details, first).category_fields["reference"] == "REF/001"
                query = dict(
                    category="government_job",
                    state="Delhi",
                    q="REF/001 Test",
                    qualification="Graduate",
                    sort="title",
                    limit=1,
                )
                one = await api.get(f"{root}/opportunities", params=query)
                two = await api.get(f"{root}/opportunities", params={**query, "page": 2})
                assert one.status_code == two.status_code == 200, (one.text, two.text)
                assert one.json()["total"] == 2
                assert {one.json()["items"][0]["id"], two.json()["items"][0]["id"]} == {
                    first,
                    second,
                }
                token = one.json()["next_cursor"]
                continuation = await api.get(
                    f"{root}/opportunities",
                    params={**query, "cursor": token},
                )
                assert continuation.status_code == 200, continuation.text
                assert continuation.json()["items"] == two.json()["items"]
                assert continuation.json()["next_cursor"] is None
                invalid_cursor = await api.get(
                    f"{root}/opportunities",
                    params={**query, "cursor": token, "sort": "newest"},
                )
                assert invalid_cursor.status_code == 422
                assert one.json()["facets"]["state"] == ["Delhi"]
                empty = await api.get(
                    f"{root}/opportunities", params={**query, "category": "result"}
                )
                assert empty.json()["items"] == []
                changed = await api.post(
                    f"{admin}/{first}/transitions",
                    json=dict(version=version, action="withdraw", reason="test"),
                    headers=editor,
                )
                assert changed.status_code == 200, changed.text
                assert (await api.get(f"{root}/opportunities/{first}")).json()[
                    "status"
                ] == "withdrawn"
                assert (await api.get(f"{root}/opportunities", params=query)).json()["total"] == 1
                connection.execute(
                    update(schema.jobs)
                    .where(schema.jobs.c.id == second)
                    .values(expires_at=func.now())
                )
                expired = await api.get(f"{root}/opportunities/{second}")
                assert expired.json()["status"] == "expired"
                assert expired.json()["apply_url"] is None
                assert (await api.get(f"{root}/opportunities", params=query)).json()["total"] == 0
                events = (await api.get(f"{root}/opportunities/{first}/history")).json()
                assert {event["event_type"] for event in events} == {"publish", "withdraw"}
                connection.execute(
                    update(schema.source_registry)
                    .where(schema.source_registry.c.id == source)
                    .values(enabled=False)
                )
                assert (await api.get(f"{root}/opportunities/{first}")).status_code == 404
        finally:
            app.dependency_overrides.clear()
            transaction.rollback()
            engine.dispose()
