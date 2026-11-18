import re
from typing import Literal
from urllib.parse import unquote, urlsplit
from uuid import UUID

from pydantic import Field, model_validator

from ..contracts import Category, Input, Short, https_origin
from .himalayas_policy import API as HIMALAYAS_API
from .himalayas_policy import NOTICES as HIMALAYAS_NOTICES

AdapterKind = Literal[
    "government_html", "government_pdf", "greenhouse", "lever", "json", "himalayas"
]


def in_scope(url: str | None, prefixes: list[str]) -> bool:
    if not url or len(url) > 2048:
        return False
    try:
        host = https_origin(url)
        parsed = urlsplit(url)
        path = unquote(parsed.path) or "/"
        if (
            parsed.fragment
            or "%" in path
            or "\\" in path
            or any(token in {".", ".."} for token in path.split("/"))
        ):
            return False
        for prefix in prefixes:
            if https_origin(prefix) == host:
                base = urlsplit(prefix).path.rstrip("/")
                if path == base or path.startswith(f"{base}/"):
                    return True
    except ValueError:
        return False
    return False


class PollConfig(Input):
    adapter: AdapterKind
    fetch_prefixes: list[str] = Field(min_length=1, max_length=8)
    notice_prefixes: list[str] = Field(min_length=1, max_length=8)
    application_prefixes: list[str] = Field(default_factory=list, max_length=8)
    interval_seconds: int = Field(default=3600, ge=300, le=604800)
    request_interval_seconds: int = Field(default=2, ge=1, le=30)
    priority: int = Field(default=0, ge=0, le=100)
    terms: Short
    approval_reference: Short
    extraction: Literal["html", "pdf", "json"]
    publication_policy: Literal["manual", "release_reviewed_ats"] = "manual"
    category: Category = "government_job"
    cycle_key: Short | None = None
    retain_excerpt: bool = False
    complete_snapshot: bool = False
    himalayas_pages: int = Field(default=2, ge=1, le=6)
    himalayas_jobs: int = Field(default=40, ge=1, le=120)
    himalayas_india_search: bool = True
    himalayas_status_checks: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def check_scope(self):
        for prefix in self.fetch_prefixes + self.notice_prefixes + self.application_prefixes:
            parts = urlsplit(prefix)
            if parts.query or not in_scope(prefix, [prefix]) or "%" in parts.path:
                raise ValueError("Prefixes must be canonical HTTPS URL paths.")
        expected = {
            "government_html": "html",
            "government_pdf": "pdf",
            "greenhouse": "json",
            "lever": "json",
            "json": "json",
            "himalayas": "json",
        }
        if self.extraction != expected[self.adapter]:
            raise ValueError("Extraction permission must match the adapter.")
        if self.adapter.startswith("government") and not self.cycle_key:
            raise ValueError("Government HTML and PDF require an explicitly scoped cycle.")
        if self.publication_policy == "release_reviewed_ats" and self.adapter not in {
            "greenhouse",
            "lever",
        }:
            raise ValueError("Only approved ATS adapters can release reviewed drafts.")
        if self.complete_snapshot and self.adapter not in {"greenhouse", "json"}:
            raise ValueError("This adapter cannot attest complete snapshots.")
        if self.adapter == "himalayas" and (
            self.interval_seconds < 86400
            or self.fetch_prefixes != [HIMALAYAS_API]
            or self.notice_prefixes != [HIMALAYAS_NOTICES]
            or self.application_prefixes != [HIMALAYAS_NOTICES]
        ):
            raise ValueError("Himalayas requires daily polling and exact documented URL scopes.")
        return self

    def validate_endpoint(self, url: str):
        if not in_scope(url, self.fetch_prefixes):
            raise ValueError("Endpoint falls outside the recorded fetch scope.")
        parts = urlsplit(url)
        if self.adapter == "himalayas" and url != HIMALAYAS_API:
            raise ValueError("Use the canonical Himalayas Browse endpoint.")
        if self.adapter == "greenhouse" and (
            parts.hostname != "boards-api.greenhouse.io"
            or not re.fullmatch(r"/v1/boards/[\w-]+/jobs", parts.path, re.ASCII)
            or parts.query not in {"", "content=true"}
        ):
            raise ValueError("Use a single approved Greenhouse job board endpoint.")
        if self.adapter == "lever" and (
            parts.hostname not in {"api.lever.co", "api.eu.lever.co"}
            or not re.fullmatch(r"/v0/postings/[\w-]+", parts.path, re.ASCII)
            or parts.query != "mode=json"
        ):
            raise ValueError("Use a single approved Lever postings endpoint in JSON mode.")


class SourceInput(Input):
    slug: Short = Field(max_length=160, pattern=r"^[a-z0-9][a-z0-9-]*$")
    organisation_id: UUID
    endpoint_url: str = Field(max_length=2048)
    config: PollConfig
    enabled: bool = False

    @model_validator(mode="after")
    def check_endpoint(self):
        self.config.validate_endpoint(self.endpoint_url)
        if self.config.adapter == "himalayas" and self.slug != "himalayas":
            raise ValueError("Register Himalayas once using the slug himalayas.")
        return self
