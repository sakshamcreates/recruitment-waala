"""Bounded integration with the public Himalayas remote jobs API."""

import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import urlencode

from pydantic import ValidationError

from ..contracts import Draft, now
from .adapters import Adapter, Discovery, digest, label, plain
from .himalayas_policy import API, allows_apply, identity
from .transport import FetchError

EMPLOYMENT = {
    "Full Time": "Full-time",
    "Part Time": "Part-time",
    "Contractor": "Contract",
    "Temporary": "Temporary",
    "Intern": "Internship",
    "Volunteer": "Volunteer",
    "Other": "Other",
}


def offset(value):
    if type(value) in {float, int} and -12 <= value <= 14:
        return value
    if isinstance(value, str) and (
        match := re.fullmatch(r"(?:UTC)?([+-])(\d{1,2}):(\d{2})", value)
    ):
        hour, minute = int(match[2]), int(match[3])
        if hour <= 14 and minute < 60:
            return (hour + minute / 60) * (-1 if match[1] == "-" else 1)
    return None


def eligibility(row):
    locations, zones = row.get("locationRestrictions"), row.get("timezoneRestrictions")
    if not isinstance(locations, list) or not isinstance(zones, list):
        return None
    countries = []
    for country in locations:
        if isinstance(country, dict):
            code = country.get("alpha2")
            if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z]{2}", code):
                return None
            countries.append(code.casefold())
        elif isinstance(country, str) and country.strip():
            token = country.strip().casefold()
            if token in {"worldwide", "asia", "apac", "anywhere", "global", "emea"}:
                return None
            countries.append(token)
        else:
            return None
    offsets = [offset(zone) for zone in zones]
    if any(zone is None for zone in offsets):
        return None
    return (not countries or "india" in countries or "in" in countries) and (
        not offsets or 5.5 in offsets
    )


def timestamp(value):
    if type(value) not in {int, float}:
        return None
    try:
        return datetime.fromtimestamp(value, UTC)
    except (ValueError, OSError, OverflowError):
        return None


def salary(row):
    currency, period = row.get("currency"), row.get("salaryPeriod")
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        return None
    if period not in ("hourly", "weekly", "fortnightly", "monthly", "annual"):
        return None
    amounts = []
    for key in ("minSalary", "maxSalary"):
        value = row.get(key)
        amounts.append(
            Decimal(str(value)) if type(value) in {float, int} and 0 < value < 10**12 else None
        )
    low, high = amounts
    if low and high and low > high:
        return None
    if not (low or high):
        return None
    text = (
        f"{low:,}–{high:,}"
        if low and high and low != high
        else (f"{low:,}" if low and high else f"from {low:,}" if low else f"up to {high:,}")
    )
    return f"{currency} {text} ({period})"


class HimalayasAdapter(Adapter):
    def __init__(self, config, url, organisation):
        super().__init__(config, url, organisation)
        self.counts = dict(fetched=0, india_eligible=0, excluded=0, uncertain=0, status_checked=0)

    def parse(self, raw):
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError
            return data
        except (ValueError, RecursionError):
            raise FetchError("invalid_feed_shape") from None

    def normalise(self, raw):
        guid = raw.get("guid")
        company = identity(guid)
        apply = raw.get("applicationLink")
        if not company or company[0] != raw.get("companySlug") or not allows_apply(guid, apply):
            raise ValueError("Provider identity or application URL is unavailable")
        name = label(raw.get("companyName"))
        if not name:
            raise ValueError("Provider employer is unavailable")
        expires = timestamp(raw.get("expiryDate"))
        return Draft(
            organisation_id=self.organisation,
            cycle_key=f"himalayas:{digest(guid)}",
            opportunity_key="posting",
            title=label(raw.get("title")),
            description=plain(raw.get("excerpt"), 12000),
            official_url=guid,
            apply_url=apply,
            expires_at=expires,
            details={
                "category": "corporate_job",
                "mode": "Remote",
                "employment": EMPLOYMENT.get(raw.get("employmentType")),
                "salary": salary(raw),
            },
        ), {
            "provider": "himalayas",
            "company_slug": company[0],
            "company_name": name,
            "india_eligible": True,
            "worldwide": raw["locationRestrictions"] == [],
            "location_restrictions": raw["locationRestrictions"],
            "timezone_restrictions": raw["timezoneRestrictions"],
            **{
                key: [value for item in raw[key][:30] if (value := label(item))]
                for key in ("seniority", "categories", "parentCategories")
                if isinstance(raw.get(key), list)
            },
            "provider_updated_at": updated.isoformat()
            if (updated := timestamp(raw.get("pubDate")))
            else None,
            "employment_type": label(raw.get("employmentType")),
            "salary_currency": label(raw.get("currency")),
            "salary_period": label(raw.get("salaryPeriod")),
            **{
                key: raw[key]
                for key in ("minSalary", "maxSalary")
                if type(raw.get(key)) in {float, int} and 0 < raw[key] < 10**12
            },
        }

    def validate(self, raw):
        if not isinstance(raw, dict):
            return None
        guid = raw.get("guid")
        eligible = eligibility(raw)
        if eligible is True:
            self.counts["india_eligible"] += 1
        if eligible is False:
            self.counts["excluded"] += 1
            return None
        try:
            if eligible is not True:
                raise ValueError
            draft, provenance = self.normalise(raw)
            if draft.expires_at and draft.expires_at <= now():
                return None
            return Discovery(digest(guid), guid, draft, provenance)
        except (ValidationError, ValueError, TypeError):
            self.counts["uncertain"] += 1
            if identity(guid):
                return Discovery(
                    digest(guid),
                    guid,
                    None,
                    {
                        "provider": "himalayas",
                        "india_eligible": False,
                        "error": "provider_record_requires_review",
                    },
                )
        return None

    def discover(self, transport, *, status_guids=()):
        items = {}
        cursors = set()
        cursor = None
        india_search = self.config.himalayas_india_search and self.config.himalayas_jobs >= 40
        browse_budget = self.config.himalayas_jobs - (20 if india_search else 0)
        for _ in range(self.config.himalayas_pages):
            limit = min(20, browse_budget - self.counts["fetched"])
            if limit <= 0:
                break
            query = {"limit": limit, **({"cursor": cursor} if cursor else {})}
            payload = self.parse(transport.fetch(f"{API}?{urlencode(query)}", self.media))
            rows = payload.get("jobs")
            if not isinstance(rows, list) or len(rows) > limit:
                raise FetchError("invalid_feed_shape")
            self.counts["fetched"] += len(rows)
            for row in rows:
                if item := self.validate(row):
                    items[item.notice_url] = item
            cursor = payload.get("nextCursor")
            if cursor is None:
                break
            if not isinstance(cursor, str) or not 0 < len(cursor) <= 1024 or cursor in cursors:
                raise FetchError("invalid_provider_cursor")
            cursors.add(cursor)
        if india_search:
            payload = self.parse(transport.fetch(f"{API}/search?country=IN", self.media))
            rows = payload.get("jobs")
            if not isinstance(rows, list) or len(rows) > 20:
                raise FetchError("invalid_feed_shape")
            self.counts["fetched"] += len(rows)
            for row in rows:
                if item := self.validate(row):
                    items[item.notice_url] = item
        closed = {}
        for guid in status_guids:
            company = identity(guid)
            if not company:
                continue
            try:
                data = self.parse(
                    transport.fetch(f"{API}/companies/{company[0]}/jobs/{company[1]}", self.media)
                )
            except FetchError as exc:
                if exc.code in {"http_404", "http_410"}:
                    self.counts["status_checked"] += 1
                    if exc.code == "http_410":
                        closed[guid] = "provider_confirmed_closed"
                        items.pop(guid, None)
                    continue
                raise
            record = data.get("job")
            if not isinstance(record, dict) or record.get("guid") != guid:
                raise FetchError("invalid_provider_status")
            self.counts["status_checked"] += 1
            if eligibility(record) is False:
                closed[guid] = "provider_confirmed_outside_india"
                items.pop(guid, None)
            else:
                # Status refreshes are counted separately from feed eligibility.
                before = {
                    key: self.counts[key] for key in ("india_eligible", "excluded", "uncertain")
                }
                replacement = self.validate(record)
                self.counts.update(before)
                if replacement:
                    items[guid] = replacement
        return list(items.values()), closed
