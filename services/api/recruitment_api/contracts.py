from datetime import UTC, datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_validator

Category = Literal[
    "government_job",
    "corporate_job",
    "internship",
    "result",
    "admit_card",
    "answer_key",
    "syllabus",
]
CATEGORIES = (
    "government_job",
    "corporate_job",
    "internship",
    "result",
    "admit_card",
    "answer_key",
    "syllabus",
)
Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Common(Input):
    state: Short | None = None


class Government(Common):
    category: Literal["government_job"]
    reference: Short | None = None
    qualification: Short | None = None
    employment: Literal["Permanent", "Contract"] | None = None
    age: Short | None = None
    fee: Short | None = None
    vacancies: int | None = Field(default=None, ge=0)
    salary: Short | None = None


class Corporate(Common):
    category: Literal["corporate_job"]
    experience: Short | None = None
    mode: Literal["On-site", "Hybrid", "Remote"] | None = None
    employment: Literal["Full-time", "Contract"] | None = None
    skills: list[Short] = Field(default_factory=list, max_length=30)
    salary: Short | None = None


class Internship(Common):
    category: Literal["internship"]
    duration: Short | None = None
    compensation: Literal["Paid", "Unpaid"] | None = None
    skills: list[Short] = Field(default_factory=list, max_length=30)
    stipend: Short | None = None


class Exam(Common):
    category: Literal["result", "admit_card", "answer_key", "syllabus"]
    stage: Short | None = None
    exam_on: AwareDatetime | None = None


Fields = Annotated[Government | Corporate | Internship | Exam, Field(discriminator="category")]


def https_origin(value: str) -> str:
    import ipaddress
    import re

    if not value.isascii() or any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value:
        raise ValueError("Use an absolute HTTPS URL on an approved public hostname.")
    parts = urlsplit(value)
    host = parts.hostname or ""
    if (
        parts.scheme != "https"
        or parts.username is not None
        or parts.password is not None
        or parts.port not in (None, 443)
        or "%" in parts.netloc
        or not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", host)
        or not re.fullmatch(r"[a-z]{2,63}", host.rsplit(".", 1)[-1])
        or host.endswith((".localhost", ".local", ".internal", ".test", ".example", ".invalid"))
    ):
        raise ValueError("Use an absolute HTTPS URL on an approved public hostname.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return host
    raise ValueError("IP addresses are unavailable as official destinations.")


class Draft(Input):
    organisation_id: UUID
    cycle_key: Short
    opportunity_key: Short
    title: Short
    details: Fields
    description: str | None = Field(default=None, max_length=12000)
    location: Short | None = None
    deadline: AwareDatetime | None = None
    expires_at: AwareDatetime | None = None
    official_url: str | None = Field(default=None, max_length=2048)
    apply_url: str | None = Field(default=None, max_length=2048)

    @field_validator("official_url", "apply_url")
    @classmethod
    def validate_url(cls, value):
        if value is not None:
            https_origin(value)
        return value


class DraftUpdate(Draft):
    version: int = Field(ge=1)


class Transition(Input):
    version: int = Field(ge=1)
    action: Literal["submit", "approve", "reject", "publish", "withdraw"]
    reason: Short
    source_item_id: UUID | None = None


class Query(Input):
    q: str = Field(default="", max_length=120)
    category: Category | None = None
    state: Short | None = None
    qualification: Short | None = None
    organisation: Short | None = None
    experience: Short | None = None
    type: Short | None = None
    mode: Literal["On-site", "Hybrid", "Remote"] | None = None
    duration: Short | None = None
    deadline: Literal["week", "month"] | None = None
    sort: Literal["newest", "title", "deadline"] = "newest"
    cursor: str | None = Field(default=None, max_length=2048)
    page: int = Field(default=1, ge=1, le=10000)
    limit: int = Field(default=20, ge=1, le=100)


class Attribution(BaseModel):
    source: str
    official_url: str | None
    observed_at: datetime
    verified_at: datetime


class Opportunity(BaseModel):
    id: UUID
    title: str
    organisation: str
    description: str | None
    location: str | None
    status: Literal["published", "expired", "withdrawn"]
    published_at: datetime
    deadline: datetime | None
    apply_url: str | None
    details: Fields
    provenance: Attribution


class Page(BaseModel):
    items: list[Opportunity]
    total: int
    page: int
    limit: int
    facets: dict[str, list[str]]
    next_cursor: str | None


class PublicChange(BaseModel):
    id: UUID
    job_id: UUID
    event_type: Literal["publish", "withdraw", "correction"]
    recorded_at: datetime


class DraftState(BaseModel):
    id: UUID
    status: str
    review_state: str
    version: int


def now() -> datetime:
    return datetime.now(UTC)
