import re
from urllib.parse import urlsplit

ORIGIN = "https://himalayas.app"
API = ORIGIN + "/jobs/api"
NOTICES = ORIGIN + "/companies"
SLUG = r"[a-z0-9][a-z0-9-]{0,199}"
JOB_PATH = rf"/companies/({SLUG})/jobs/({SLUG})"


def identity(guid: object) -> tuple[str, str] | None:
    if not isinstance(guid, str) or not guid.startswith(ORIGIN + "/"):
        return None
    match = re.fullmatch(JOB_PATH, guid.removeprefix(ORIGIN))
    return (match[1], match[2]) if match else None


def allows_apply(guid: str | None, url: str | None) -> bool:
    if not identity(guid) or not url or len(url) > 2048:
        return False
    if not url.isascii() or any(char.isspace() or ord(char) < 33 for char in url):
        return False
    target = urlsplit(url)
    return (
        url.startswith(ORIGIN + "/")
        and not target.fragment
        and target.path in {urlsplit(guid).path, urlsplit(guid).path + "/apply"}
    )


def is_api_url(url: str) -> bool:
    if not url.startswith(API):
        return False
    path = urlsplit(url).path
    return path in {"/jobs/api", "/jobs/api/search"} or bool(
        re.fullmatch("/jobs/api" + JOB_PATH, path)
    )


def employer_slug(company: str) -> str:
    import hashlib

    return "himalayas-employer-" + hashlib.sha256(company.encode()).hexdigest()
