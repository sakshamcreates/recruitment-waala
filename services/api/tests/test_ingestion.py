import io
import json
import socket
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from ingestion.celery_app import dispatch, poll
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from recruitment_api import schema
from recruitment_api.contracts import now
from recruitment_api.ingestion import runner
from recruitment_api.ingestion.adapters import ADAPTERS
from recruitment_api.ingestion.policy import PollConfig, in_scope
from recruitment_api.ingestion.transport import FetchError, public_address
from recruitment_api.main import app
from sqlalchemy import func, insert, select, update

ROOT = "/api/v1/admin/ingestion"
ORIGIN = "https://www.upsc.gov.in"
ENDPOINT = ORIGIN + "/authorised-fixture"
NOTICE = ORIGIN + "/notices/fixture"
ORG = uuid4()


def configuration(adapter="json", **changes):
    return PollConfig.model_validate(
        {
            "adapter": adapter,
            "fetch_prefixes": [ORIGIN],
            "notice_prefixes": [ORIGIN + "/notices"],
            "application_prefixes": [ORIGIN + "/notices"],
            "terms": "Offline deterministic test only",
            "approval_reference": "Test permission fixture",
            "extraction": {"government_pdf": "pdf", "government_html": "html"}.get(adapter, "json"),
            "cycle_key": "round-a",
            **changes,
        }
    )


class FixtureTransport:
    def __init__(self, payload):
        self.payload = payload

    def fetch(self, url, media):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def record(cycle="round-a", vacancy=4, deadline="2040-05-01T12:00:00+05:30"):
    return {
        "external_id": "repeatable-reference",
        "draft": {
            "organisation_id": str(ORG),
            "cycle_key": cycle,
            "opportunity_key": "post-code-1",
            "title": "Offline test opportunity",
            "official_url": NOTICE,
            "apply_url": NOTICE,
            "deadline": deadline,
            "details": {
                "category": "government_job",
                "reference": "DEMO-REF",
                "vacancies": vacancy,
            },
        },
    }


def test_ats_adapters_require_scoped_official_urls():
    green = configuration(
        "greenhouse",
        fetch_prefixes=[
            "https://boards-api.greenhouse.io/v1/boards/sample/jobs",
        ],
    )
    url = "https://boards-api.greenhouse.io/v1/boards/sample/jobs?content=true"
    green.validate_endpoint(url)
    with pytest.raises(ValueError):
        green.validate_endpoint(url.replace("/sample/", "/outside/"))
    adapter = ADAPTERS["greenhouse"](green, url, ORG)
    body = {
        "jobs": [
            {
                "id": 21,
                "title": "Role",
                "absolute_url": NOTICE,
                "content": "<p>Plain</p><script>Ignore</script>",
                "departments": [{"name": "Operations"}],
            }
        ]
    }
    item = adapter.discover(FixtureTransport(json.dumps(body).encode()))[0]
    assert item.draft.description == "Plain"
    assert item.draft.details.salary is None
    assert item.provenance["fields"]["department"] == "Operations"
    body["jobs"][0]["absolute_url"] = "https://other.org/notices/fixture"
    assert adapter.discover(FixtureTransport(json.dumps(body).encode()))[0].draft is None
    lever = configuration("lever", fetch_prefixes=["https://api.lever.co/v0/postings/sample"])
    url = "https://api.lever.co/v0/postings/sample?mode=json"
    lever.validate_endpoint(url)
    payload = [
        {
            "id": "posting-1",
            "text": "Role",
            "hostedUrl": NOTICE,
            "workplaceType": "hybrid",
            "categories": {"commitment": "Full-time"},
        }
    ]
    result = (
        ADAPTERS["lever"](lever, url, ORG)
        .discover(FixtureTransport(json.dumps(payload).encode()))[0]
        .draft
    )
    assert result.details.mode == "Hybrid" and result.details.employment == "Full-time"
    assert result.apply_url is None


def test_government_html_and_pdf():
    links = b'<a href="/notices/fixture">Offline notice</a><a href="/private">Ignore</a>'
    html = ADAPTERS["government_html"](configuration("government_html"), ENDPOINT, ORG)
    assert [item.draft.title for item in html.discover(FixtureTransport(links))] == [
        "Offline notice"
    ]
    adapter = ADAPTERS["government_pdf"](configuration("government_pdf"), NOTICE, ORG)
    assert adapter.discover(FixtureTransport(b"invalid PDF"))[0].draft is None
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {
                    NameObject("/F1"): DictionaryObject(
                        {
                            NameObject("/Type"): NameObject("/Font"),
                            NameObject("/Subtype"): NameObject("/Type1"),
                            NameObject("/BaseFont"): NameObject("/Helvetica"),
                        }
                    ),
                }
            ),
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 72 720 Td (Recruitment title: Offline notice) Tj "
        b"0 -20 Td (Notification number: DEMO-1) Tj 0 -20 Td (Vacancies: 7) Tj ET"
    )
    page[NameObject("/Contents")] = stream
    buffer = io.BytesIO()
    writer.write(buffer)
    result = adapter.discover(FixtureTransport(buffer.getvalue()))[0].draft
    assert result.details.vacancies == 7 and result.details.reference == "DEMO-1"
    assert result.deadline is None


def test_network_scope_and_private_resolution(monkeypatch):
    assert not in_scope(ORIGIN + "/notices/%2e%2e/private", [ORIGIN + "/notices"])
    assert not in_scope(ORIGIN + "/notices-copy/fixture", [ORIGIN + "/notices"])
    assert not in_scope("https://user@www.upsc.gov.in/notices", [ORIGIN])
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ],
    )
    with pytest.raises(FetchError, match="nonpublic_address"):
        public_address("www.upsc.gov.in")


def test_dispatch_and_retry_boundaries(monkeypatch):
    scheduled = []
    monkeypatch.setattr(runner, "due_sources", lambda: [ORG])
    monkeypatch.setattr(poll, "apply_async", lambda **kwargs: scheduled.append(kwargs))
    dispatch()
    assert scheduled == [{"args": [str(ORG)], "expires": 180}]

    def fail(source_id):
        raise FetchError("timeout", retry=True, retry_after=47)

    monkeypatch.setattr(runner, "run_source", fail)
    retries = []
    monkeypatch.setattr(poll, "retry", lambda **kwargs: retries.append(kwargs) or RuntimeError())
    with pytest.raises(RuntimeError):
        poll(str(ORG))
    assert retries == [{"countdown": 48}]
    poll.push_request(retries=3)
    try:
        assert poll.run(str(ORG)) == {"state": "failed", "code": "timeout"}
    finally:
        poll.pop_request()


@pytest.mark.anyio
async def test_ingestion_to_publication_and_corrections(ingestion_db, monkeypatch):
    monkeypatch.setenv("RW_ENV", "development")
    monkeypatch.setenv("RW_ADMIN_ENABLED", "true")
    token = uuid4().hex
    monkeypatch.setenv("RW_ADMIN_TOKEN", token)
    headers = {"Authorization": f"Bearer {token}"}
    with ingestion_db.begin() as db:
        db.execute(
            insert(schema.organisations).values(id=ORG, slug="offline-test", name="Test Issuer")
        )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        config = configuration(complete_snapshot=True)
        source = {
            "slug": "offline-test",
            "organisation_id": str(ORG),
            "endpoint_url": ENDPOINT,
            "config": config.model_dump(mode="json"),
        }
        assert (await client.post(f"{ROOT}/sources", json=source)).status_code == 401
        registered = await client.post(f"{ROOT}/sources", json=source, headers=headers)
        assert registered.status_code == 201, registered.text
        from uuid import UUID

        source_id = UUID(registered.json()["id"])

        def due():
            with ingestion_db.begin() as db:
                db.execute(
                    update(runner.polling)
                    .where(runner.polling.c.source_id == source_id)
                    .values(next_poll_at=now())
                )

        def collect(rows):
            due()
            return runner.run_source(
                source_id, lambda _: FixtureTransport(json.dumps(rows).encode())
            )

        assert collect([record()])["state"] == "not_due_or_disabled"
        assert (
            await client.patch(
                f"{ROOT}/sources/{source_id}", json={"enabled": True}, headers=headers
            )
        ).status_code == 200
        assert source_id in runner.due_sources()
        assert collect([record(), record()])["created"] == 1
        assert collect([record()])["duplicate"] == 1
        assert (await client.get("/api/v1/opportunities")).json()["total"] == 0

        async def pending():
            response = await client.get(f"{ROOT}/candidates", headers=headers)
            assert response.status_code == 200, response.text
            return response.json()

        async def accept(candidate):
            response = await client.post(
                f"{ROOT}/candidates/{candidate['item_id']}/review",
                headers=headers,
                json={
                    "version": candidate["version"],
                    "reason": "Checked fixture",
                    "action": "accept",
                },
            )
            assert response.status_code == 200, response.text
            return response.json()

        initial = (await pending())[0]
        job_id = initial["job_id"]
        assert (
            await client.post(
                f"{ROOT}/candidates/{initial['item_id']}/review",
                json={"action": "accept", "reason": "No token"},
            )
        ).status_code == 401
        approved = await accept(initial)
        published = await client.post(
            f"/api/v1/admin/opportunities/{job_id}/transitions",
            headers=headers,
            json={
                "version": approved["version"],
                "action": "publish",
                "reason": "Fixture approval",
            },
        )
        assert published.status_code == 200, published.text
        detail = await client.get(f"/api/v1/opportunities/{job_id}")
        assert detail.json()["details"]["vacancies"] == 4
        updated = record(vacancy=9, deadline="2040-06-01T12:00:00+05:30")
        assert collect([updated, record("round-b")])["updated"] == 1
        assert (await client.get(f"/api/v1/opportunities/{job_id}")).json()["details"][
            "vacancies"
        ] == 4
        correction = next(row for row in await pending() if row["job_id"] == job_id)
        assert correction["payload"]["deadline"] != initial["payload"]["deadline"]
        await accept(correction)
        corrected = (await client.get(f"/api/v1/opportunities/{job_id}")).json()
        assert corrected["details"]["vacancies"] == 9
        assert corrected["deadline"].startswith("2040-06-01")
        assert collect([{"external_id": "broken"}, record("round-b")])["state"] == "partial"
        assert not any(row["state"] == "withdrawal_review" for row in await pending())
        assert collect([record("round-b")])["pending_review"] == 1
        candidate = next(row for row in await pending() if row["state"] == "withdrawal_review")
        await accept(candidate)
        assert (await client.get(f"/api/v1/opportunities/{job_id}")).json()["status"] == "withdrawn"
        assert (await client.get("/api/v1/opportunities")).json()["total"] == 0
        history = (await client.get(f"/api/v1/opportunities/{job_id}/history")).json()
        assert {event["event_type"] for event in history} == {"publish", "correction", "withdraw"}

        due()
        with pytest.raises(FetchError, match="timeout"):
            runner.run_source(
                source_id, lambda _: FixtureTransport(FetchError("timeout", retry=True))
            )
        assert runner.run_source(source_id)["state"] == "not_due_or_disabled"
        report = (await client.get(f"{ROOT}/runs", headers=headers)).json()
        assert report[0]["error_code"] == "timeout" and report[0]["counts"]["http_failures"] == 1
        monitor = (await client.get(f"{ROOT}/sources", headers=headers)).json()
        assert monitor[0]["health"] == "degraded" and monitor[0]["consecutive_failures"] == 1

        due()
        started, finish = Event(), Event()

        class Blocking(FixtureTransport):
            def fetch(self, url, media):
                started.set()
                assert finish.wait(10)
                return super().fetch(url, media)

        with ThreadPoolExecutor(max_workers=2) as pool:
            pending_run = pool.submit(
                runner.run_source,
                source_id,
                lambda _: Blocking(json.dumps([record("round-b")]).encode()),
            )
            try:
                assert started.wait(5)
                assert runner.run_source(source_id)["state"] == "locked"
            finally:
                finish.set()
            assert pending_run.result(timeout=10)["duplicate"] == 1
        with ingestion_db.connect() as db:
            assert db.scalar(select(func.count()).select_from(schema.jobs)) == 2


@pytest.mark.anyio
async def test_opted_in_ats_release_requires_manual_review(ingestion_db, monkeypatch):
    from uuid import UUID

    from recruitment_api.ingestion import release

    monkeypatch.setattr(release, "engine", lambda: ingestion_db)
    monkeypatch.setenv("RW_ENV", "development")
    monkeypatch.setenv("RW_ADMIN_ENABLED", "true")
    token = uuid4().hex
    monkeypatch.setenv("RW_ADMIN_TOKEN", token)
    auth = {"Authorization": f"Bearer {token}"}
    with pytest.raises(ValueError, match="Only approved ATS adapters"):
        configuration(publication_policy="release_reviewed_ats")
    with ingestion_db.begin() as connection:
        connection.execute(
            insert(schema.organisations).values(
                id=ORG,
                slug="offline-employer",
                name="Offline employer",
            )
        )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for board, policy in (("manual", "manual"), ("opted-in", "release_reviewed_ats")):
            endpoint = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
            config = configuration(
                "greenhouse", fetch_prefixes=[endpoint], publication_policy=policy
            )
            source = await client.post(
                f"{ROOT}/sources",
                headers=auth,
                json={
                    "slug": board,
                    "organisation_id": str(ORG),
                    "endpoint_url": endpoint,
                    "config": config.model_dump(mode="json"),
                    "enabled": True,
                },
            )
            assert source.status_code == 201, source.text
            source_id = source.json()["id"]
            fixture = {"jobs": [{"id": 1, "title": board, "absolute_url": NOTICE}]}
            assert (
                runner.run_source(
                    UUID(source_id),
                    lambda _, fixture=fixture: FixtureTransport(json.dumps(fixture).encode()),
                )["created"]
                == 1
            )
            assert release.release_reviewed() == 0
            candidates = (
                await client.get(f"{ROOT}/candidates?source_id={source_id}", headers=auth)
            ).json()
            candidate = candidates[0]
            response = await client.post(
                f"{ROOT}/candidates/{candidate['item_id']}/review",
                headers=auth,
                json={
                    "action": "accept",
                    "reason": "Compared offline evidence",
                    "version": candidate["version"],
                },
            )
            assert response.status_code == 200, response.text
        assert release.release_reviewed() == 1
        assert release.release_reviewed() == 0
        public = (await client.get("/api/v1/opportunities")).json()
        assert [row["title"] for row in public["items"]] == ["opted-in"]
