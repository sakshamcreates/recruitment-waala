import json
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from recruitment_api import schema
from recruitment_api.contracts import now
from recruitment_api.ingestion import runner
from recruitment_api.ingestion.himalayas import HimalayasAdapter, eligibility, salary
from recruitment_api.ingestion.himalayas_policy import API, NOTICES, ORIGIN
from recruitment_api.ingestion.policy import PollConfig
from recruitment_api.ingestion.transport import FetchError
from recruitment_api.main import app
from sqlalchemy import func, insert, select, update

GUID = ORIGIN + "/companies/offline-employer/jobs/test-fixture"
APPLY = GUID + "?utm_source=api&tracking=a%2Fb"


def job(**changes):
    return {
        "title": "Offline fixture role",
        "companySlug": "offline-employer",
        "companyName": "Offline fixture employer",
        "guid": GUID,
        "applicationLink": APPLY,
        "locationRestrictions": [{"alpha2": "IN", "name": "India", "slug": "india"}],
        "timezoneRestrictions": ["+05:30"],
        "employmentType": "Full Time",
        "excerpt": "Offline test data",
        "minSalary": 35,
        "maxSalary": 60,
        "currency": "USD",
        "salaryPeriod": "hourly",
        "pubDate": 1795000000,
        "expiryDate": 2200000000,
        "seniority": ["Senior"],
        "categories": ["Engineering"],
        **changes,
    }


def config(**changes):
    return PollConfig(
        adapter="himalayas",
        extraction="json",
        fetch_prefixes=[API],
        notice_prefixes=[NOTICES],
        application_prefixes=[NOTICES],
        interval_seconds=86400,
        approval_reference="Isolated test fixture only",
        terms="Isolated fixture only",
        **changes,
    )


class Transport:
    def __init__(self, pages, status=None):
        self.pages = iter(pages)
        self.status = status
        self.urls = []

    def fetch(self, url, media):
        self.urls.append(url)
        value = self.status if "/companies/" in url else next(self.pages)
        if isinstance(value, FetchError):
            raise value
        return json.dumps(value).encode()


@pytest.mark.parametrize(
    ("locations", "zones", "expected"),
    [
        ([], [], True),
        (["India"], [5.5], True),
        ([{"alpha2": "IN"}], ["UTC+05:30"], True),
        (["Vietnam"], [], False),
        (["India"], [7], False),
        ([], [7], False),
        (None, [], None),
        (["Asia"], [], None),
        ([], ["invalid"], None),
    ],
)
def test_india_eligibility(locations, zones, expected):
    assert eligibility(job(locationRestrictions=locations, timezoneRestrictions=zones)) is expected


def test_cursor_budget_salary_and_exact_application_url():
    adapter = HimalayasAdapter(config(himalayas_jobs=3), API, uuid4())
    cursor = "opaque+/== number"
    transport = Transport(
        [
            {"jobs": [job(), job(locationRestrictions=["Vietnam"])], "nextCursor": cursor},
            {"jobs": [job(applicationLink="https://employer.org/apply")]},
        ]
    )
    rows, closed = adapter.discover(transport)
    assert parse_qs(urlsplit(transport.urls[1]).query) == {"cursor": [cursor], "limit": ["1"]}
    assert not closed and adapter.counts["fetched"] == 3
    assert adapter.counts["excluded"] == 1 and adapter.counts["uncertain"] == 1
    single = HimalayasAdapter(config(himalayas_jobs=1), API, uuid4())
    result, _ = single.discover(Transport([{"jobs": [job()]}]))
    assert result[0].draft.apply_url == APPLY
    assert result[0].draft.details.salary == "USD 35–60 (hourly)"
    assert result[0].draft.details.mode == "Remote"
    assert result[0].draft.deadline is None
    assert result[0].provenance["seniority"] == ["Senior"]
    assert salary(job(salaryPeriod="invalid")) is None
    assert (
        salary(job(minSalary=None, maxSalary=50, currency="INR", salaryPeriod="monthly"))
        == "INR up to 50 (monthly)"
    )
    assert rows[-1].draft is None


def test_india_search_and_status_semantics():
    adapter = HimalayasAdapter(config(), API, uuid4())
    transport = Transport([{"jobs": []}, {"jobs": [job()]}], FetchError("http_404"))
    rows, closed = adapter.discover(transport, status_guids=[GUID])
    assert transport.urls[1] == f"{API}/search?country=IN"
    assert len(rows) == 1 and closed == {}
    adapter = HimalayasAdapter(config(himalayas_jobs=1), API, uuid4())
    transport = Transport([{"jobs": [job()]}], FetchError("http_410"))
    assert adapter.discover(transport, status_guids=[GUID]) == (
        [],
        {GUID: "provider_confirmed_closed"},
    )
    for code in ("http_429", "timeout"):
        adapter = HimalayasAdapter(config(himalayas_jobs=1), API, uuid4())
        with pytest.raises(FetchError, match=code):
            adapter.discover(Transport([FetchError(code, retry=True, retry_after=30)]))


@pytest.mark.anyio
async def test_himalayas_governance_review_publication_and_closure(ingestion_db, monkeypatch):
    monkeypatch.setenv("RW_ENV", "development")
    monkeypatch.setenv("RW_ADMIN_ENABLED", "true")
    token = uuid4().hex
    monkeypatch.setenv("RW_ADMIN_TOKEN", token)
    headers = {"Authorization": f"Bearer {token}"}
    provider_id = uuid4()
    with ingestion_db.begin() as db:
        db.execute(
            insert(schema.organisations).values(
                id=provider_id,
                slug="provider-test",
                name="Himalayas provider fixture",
            )
        )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        root = "/api/v1/admin/ingestion"
        body = {
            "organisation_id": str(provider_id),
            "slug": "himalayas",
            "endpoint_url": API,
            "config": config(himalayas_jobs=4).model_dump(mode="json"),
        }
        registered = await client.post(f"{root}/sources", json=body, headers=headers)
        assert registered.status_code == 201, registered.text
        source_id = UUID(registered.json()["id"])

        def poll(rows, status=None):
            with ingestion_db.begin() as db:
                db.execute(
                    update(schema.source_polling)
                    .where(schema.source_polling.c.source_id == source_id)
                    .values(next_poll_at=now())
                )
            transport = Transport([{"jobs": rows}], status)
            return runner.run_source(source_id, lambda _: transport)

        assert poll([job()])["state"] == "not_due_or_disabled"
        enabled = await client.patch(
            f"{root}/sources/{source_id}", json={"enabled": True}, headers=headers
        )
        assert enabled.status_code == 200
        imported = poll([job(), job(locationRestrictions=["Vietnam"])])
        assert imported["created"] == 1 and imported["excluded"] == 1
        assert poll([job(pubDate=1795000060)])["duplicate"] == 1
        assert (await client.get("/api/v1/opportunities")).json()["total"] == 0
        candidates = (await client.get(f"{root}/candidates", headers=headers)).json()
        candidate = candidates[0]
        approved = await client.post(
            f"{root}/candidates/{candidate['item_id']}/review",
            headers=headers,
            json={"version": candidate["version"], "action": "accept", "reason": "Offline review"},
        )
        assert approved.status_code == 200, approved.text
        job_id = candidate["job_id"]
        transition = f"/api/v1/admin/opportunities/{job_id}/transitions"
        request = {"version": approved.json()["version"], "action": "publish", "reason": "Fixture"}
        with ingestion_db.begin() as db:
            db.execute(update(schema.job_details).values(apply_url=GUID))
        assert (await client.post(transition, json=request, headers=headers)).status_code == 422
        with ingestion_db.begin() as db:
            db.execute(update(schema.job_details).values(apply_url=APPLY))
        published = await client.post(transition, json=request, headers=headers)
        assert published.status_code == 200, published.text
        listing = (
            await client.get("/api/v1/opportunities?category=corporate_job&mode=Remote")
        ).json()
        assert listing["total"] == 1
        visible = listing["items"][0]
        assert visible["organisation"] == job()["companyName"]
        assert visible["provenance"]["provider"] == "himalayas"
        assert visible["apply_url"] == APPLY
        assert poll([], FetchError("http_404"))["status_withdrawn"] == 0
        assert (await client.get("/api/v1/opportunities")).json()["total"] == 1
        assert poll([], FetchError("http_410"))["status_withdrawn"] == 1
        detail = await client.get(f"/api/v1/opportunities/{job_id}")
        assert detail.status_code == 404
        assert (await client.get("/api/v1/opportunities")).json()["total"] == 0
    with ingestion_db.connect() as db:
        assert db.scalar(select(func.count()).select_from(schema.jobs)) == 1
        assert db.scalar(select(schema.jobs.c.status)) == "withdrawn"
