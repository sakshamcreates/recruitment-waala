import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from uuid import UUID

from pydantic import Field, ValidationError

from ..contracts import Draft, Input, Short
from .policy import PollConfig, in_scope
from .transport import FetchError, SafeTransport

MAX_ITEMS = 500


class TextHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.anchor: str | None = None
        self.label: list[str] = []
        self.hidden = False

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden = True
        elif tag == "a" and not self.hidden:
            self.anchor = dict(attrs).get("href")
            self.label = []

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = False
        elif tag == "a" and self.anchor:
            self.links.append((self.anchor, " ".join(self.label)))
            self.anchor = None

    def handle_data(self, data):
        if not self.hidden and (data := data.strip()):
            self.text.append(data)
            if self.anchor:
                self.label.append(data)


def plain(value: object, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    parser = TextHTML()
    parser.feed(value)
    parser.close()
    return " ".join(" ".join(parser.text).split())[:limit].strip() or None


def label(value: object) -> str | None:
    return plain(value, 200)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class FeedItem(Input):
    external_id: Short
    draft: Draft
    closed: bool = False
    metadata: dict[Short, Short] = Field(default_factory=dict, max_length=12)


@dataclass(frozen=True)
class Discovery:
    external_id: str
    notice_url: str
    draft: Draft | None
    provenance: dict
    closed: bool = False


class Adapter:
    media = ("application/json",)

    def __init__(self, config: PollConfig, url: str, organisation: UUID):
        self.config, self.url, self.organisation = config, url, organisation

    def fetch(self, transport: SafeTransport) -> bytes:
        return transport.fetch(self.url, self.media)

    def parse(self, raw: bytes):
        content = json.loads(raw)
        if not isinstance(content, list):
            raise FetchError("invalid_feed_shape")
        return content

    def normalise(self, raw: dict) -> FeedItem:
        return FeedItem.model_validate(raw)

    def validate(self, item: FeedItem) -> Draft:
        draft = item.draft
        if (
            draft.organisation_id != self.organisation
            or not in_scope(draft.official_url, self.config.notice_prefixes)
            or draft.apply_url
            and not in_scope(draft.apply_url, self.config.application_prefixes)
        ):
            raise ValueError("Invalid source context")
        return draft

    def discover(self, transport: SafeTransport) -> list[Discovery]:
        try:
            records = self.parse(self.fetch(transport))
        except (ValueError, RecursionError, TypeError):
            raise FetchError("parse_failed") from None
        if len(records) > MAX_ITEMS:
            raise FetchError("item_limit")
        items = []
        for offset, record in enumerate(records):
            external_id = None
            try:
                item = self.normalise(record)
                external_id = item.external_id
                draft = self.validate(item)
                items.append(
                    Discovery(
                        external_id,
                        draft.official_url,
                        draft,
                        {
                            "method": self.config.adapter,
                            "fields": item.metadata,
                            "document_url": self.url,
                            "confidence": "unverified",
                        },
                        item.closed,
                    )
                )
            except (ValidationError, ValueError, TypeError, AttributeError, KeyError):
                identity = (
                    record.get("external_id", record.get("id"))
                    if isinstance(record, dict)
                    else None
                )
                if external_id is None and isinstance(identity, (str, int)):
                    external_id = str(identity)[:200] or None
                items.append(
                    Discovery(
                        external_id or f"invalid:{digest(json.dumps(record, sort_keys=True))}",
                        self.url,
                        None,
                        {
                            "method": self.config.adapter,
                            "error": "invalid_record",
                            "position": offset,
                        },
                    )
                )
        return items


class ATSAdapter(Adapter):
    def make_job(self, record, *, title, location, description, notice, apply, details, metadata):
        identity = record["id"]
        if isinstance(identity, bool) or not isinstance(identity, (str, int)):
            raise ValueError("Invalid ATS identity")
        board = urlsplit(self.url).path.split("/")[3]
        if not in_scope(apply, self.config.application_prefixes):
            apply = None
        return FeedItem(
            external_id=str(identity),
            draft=Draft(
                organisation_id=self.organisation,
                cycle_key=f"{self.config.adapter}:{board}:{digest(str(identity))}",
                opportunity_key="posting",
                title=label(title),
                location=label(location),
                description=plain(description, 12000),
                official_url=notice,
                apply_url=apply,
                details=details,
            ),
            metadata={key: value for key, raw in metadata.items() if (value := label(raw))},
        )


class Greenhouse(ATSAdapter):
    def parse(self, raw):
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
            raise FetchError("invalid_feed_shape")
        rows = data["jobs"]
        total = data.get("meta", {}).get("total") if isinstance(data.get("meta"), dict) else None
        if self.config.complete_snapshot and total != len(rows):
            raise FetchError("incomplete_snapshot")
        return rows

    def normalise(self, raw):
        location = raw.get("location") or {}
        departments = raw.get("departments") or []
        return self.make_job(
            raw,
            title=raw["title"],
            location=location.get("name"),
            description=raw.get("content"),
            notice=raw["absolute_url"],
            apply=raw["absolute_url"],
            details={"category": "corporate_job"},
            metadata={
                "department": next(
                    (item.get("name") for item in departments if isinstance(item, dict)), None
                ),
                "updated_at": raw.get("updated_at"),
            },
        )


class Lever(ATSAdapter):
    def normalise(self, raw):
        categories = raw.get("categories") or {}
        commitment = categories.get("commitment")
        mode = {"remote": "Remote", "hybrid": "Hybrid", "on-site": "On-site"}.get(
            raw.get("workplaceType")
        )
        salary = raw.get("salaryRange") or {}
        pay = None
        if isinstance(salary, dict) and all(
            salary.get(key) is not None for key in ("currency", "min", "max", "interval")
        ):
            pay = f"{salary['currency']} {salary['min']}–{salary['max']} / {salary['interval']}"
        return self.make_job(
            raw,
            title=raw["text"],
            location=categories.get("location"),
            description=raw.get("descriptionPlain") or raw.get("description"),
            notice=raw["hostedUrl"],
            apply=raw.get("applyUrl"),
            details={
                "category": "corporate_job",
                "mode": mode,
                "employment": commitment if commitment in {"Full-time", "Contract"} else None,
                "salary": pay,
            },
            metadata={
                "department": categories.get("department") or categories.get("team"),
                "source_commitment": commitment,
            },
        )


class GovernmentHTML(Adapter):
    media = ("text/html",)

    def parse(self, raw):
        parser = TextHTML()
        parser.feed(raw.decode("utf-8"))
        parser.close()
        records = {}
        for href, title in parser.links:
            url = urljoin(self.url, href)
            if url != self.url and in_scope(url, self.config.notice_prefixes):
                records.setdefault(url, {"url": url, "title": title})
        if not records:
            raise FetchError("no_scoped_notices")
        return list(records.values())

    def normalise(self, raw):
        url = raw["url"]
        return FeedItem(
            external_id=digest(url),
            draft=Draft(
                organisation_id=self.organisation,
                cycle_key=self.config.cycle_key,
                opportunity_key=digest(url),
                title=label(raw["title"]),
                official_url=url,
                details={"category": self.config.category},
            ),
            metadata={"title": "approved HTML link text"},
        )


class GovernmentPDF(GovernmentHTML):
    media = ("application/pdf",)

    def parse(self, raw):
        try:
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("pdf_extract.py"))],
                input=raw,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=6,
                check=True,
            )
            text = result.stdout.decode().strip()
        except (subprocess.SubprocessError, UnicodeError):
            text = ""
        return [{"url": self.url, "text": text}]

    def normalise(self, raw):
        text = raw["text"]
        if not text:
            raise ValueError("PDF requires manual extraction")

        def field(name):
            match = re.search(rf"(?im)^\s*(?:{name})\s*:\s*([^\n]+)", text)
            return label(match[1]) if match else None

        title = field("Recruitment title|Post title|Post name")
        reference = field(r"Notification (?:No\.?|Number)|Advertisement (?:No\.?|Number)")
        if not title or not reference:
            raise ValueError("PDF identity requires manual review")
        item = super().normalise({"url": raw["url"], "title": title})
        # The explicit cycle and URL keep heuristic references out of canonical identity.
        details = {"category": self.config.category}
        vacancy = field("Vacancies|Vacancy count")
        if self.config.category == "government_job":
            details.update(
                reference=reference,
                qualification=field("Eligibility|Qualification"),
                age=field("Age limit"),
                fee=field("Application fee"),
                vacancies=int(vacancy)
                if vacancy and re.fullmatch(r"[0-9]{1,9}", vacancy)
                else None,
            )
        body = item.draft.model_dump()
        if self.config.retain_excerpt:
            body["description"] = plain(text, 4000)
        item.draft = Draft.model_validate({**body, "details": details})
        item.metadata = {"title": "heuristic PDF label", "reference": reference}
        for key, pattern in {
            "issuing_authority": "Department|Issuing authority",
            "application_instructions": "Application instructions",
            "deadline_text": "Deadline|Closing date|Last date",
        }.items():
            if value := field(pattern):
                item.metadata[key] = value
        for key, value in details.items():
            if key != "category" and value is not None:
                item.metadata.setdefault(key, "heuristic PDF label")
        return item


ADAPTERS = {
    "json": Adapter,
    "government_html": GovernmentHTML,
    "government_pdf": GovernmentPDF,
    "greenhouse": Greenhouse,
    "lever": Lever,
}
