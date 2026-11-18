import http.client
import ipaddress
import socket
import ssl
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from ..contracts import https_origin
from .policy import PollConfig, in_scope

AGENT = "RecruitmentWaala"
MAX_BYTES = 2_000_000


class FetchError(Exception):
    def __init__(self, code: str, *, retry=False, retry_after=0):
        super().__init__(code)
        self.code = code
        self.retry = retry
        self.retry_after = retry_after


def public_address(host: str) -> str:
    answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    addresses = [ipaddress.ip_address(row[4][0]) for row in answers]
    if not addresses or any(
        not addr.is_global
        or addr.is_multicast
        or addr.is_reserved
        or getattr(addr, "ipv4_mapped", None) is not None
        for addr in addresses
    ):
        raise FetchError("nonpublic_address")
    return str(addresses[0])


class PinnedHTTPS(http.client.HTTPSConnection):
    def connect(self):
        address = public_address(self.host)
        raw = socket.create_connection((address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


class SafeTransport:
    def __init__(self, config: PollConfig):
        self.config = config
        self.previous = 0.0
        self.robots: dict[str, RobotFileParser] = {}

    def fetch(self, url: str, media: tuple[str, ...]) -> bytes:
        if not in_scope(url, self.config.fetch_prefixes):
            raise FetchError("outside_fetch_scope")
        host = https_origin(url)
        if self.config.adapter.startswith("government"):
            if host not in self.robots:
                parser = RobotFileParser()
                parser.parse(
                    self._get(f"https://{host}/robots.txt", ("text/plain",), limit=128_000)
                    .decode("utf-8", errors="replace")
                    .splitlines()
                )
                self.robots[host] = parser
            parser = self.robots[host]
            if not parser.can_fetch(AGENT, url):
                raise FetchError("robots_denied")
        return self._get(url, media)

    def _get(self, url: str, media: tuple[str, ...], limit=MAX_BYTES) -> bytes:
        parts = urlsplit(url)
        parser = self.robots.get(https_origin(url))
        delay = (parser.crawl_delay(AGENT) or 0) if parser else 0
        if parser and (rate := parser.request_rate(AGENT)):
            if rate.requests <= 0:
                raise FetchError("robots_rate_denied")
            delay = max(delay, rate.seconds / rate.requests)
        if delay > 30:
            raise FetchError("robots_rate_requires_review")
        time.sleep(
            max(
                0,
                self.previous + max(delay, self.config.request_interval_seconds) - time.monotonic(),
            )
        )
        conn = PinnedHTTPS(https_origin(url), timeout=5, context=ssl.create_default_context())
        started = time.monotonic()
        self.previous = started
        try:
            path = parts.path or "/"
            if parts.query:
                path += "?" + parts.query
            conn.request(
                "GET",
                path,
                headers={
                    "User-Agent": AGENT,
                    "Accept-Encoding": "identity",
                    "Accept": ", ".join(media),
                },
            )
            response = conn.getresponse()
            if response.status != 200:
                retry = response.status in {408, 429, 500, 502, 503, 504}
                after = response.getheader("Retry-After", "")
                wait = int(after) if after.isdecimal() and len(after) < 10 else 0
                if after and not wait:
                    try:
                        deadline = parsedate_to_datetime(after)
                        wait = max(0, int((deadline - datetime.now(UTC)).total_seconds()))
                    except (ValueError, TypeError, OverflowError):
                        pass
                raise FetchError(f"http_{response.status}", retry=retry, retry_after=wait)
            if response.getheader("Content-Encoding", "identity").lower() != "identity":
                raise FetchError("compressed_response")
            if response.headers.get_content_type() not in media:
                raise FetchError("unexpected_media")
            length = response.getheader("Content-Length")
            if length and (not length.isdecimal() or len(length) > 10 or int(length) > limit):
                raise FetchError("response_too_large")
            content = bytearray()
            while True:
                if time.monotonic() - started > 12:
                    raise FetchError("timeout", retry=True)
                chunk = response.read1(min(65536, limit + 1 - len(content)))
                if not chunk:
                    break
                content.extend(chunk)
                if len(content) > limit:
                    raise FetchError("response_too_large")
            if length and len(content) != int(length):
                raise FetchError("truncated_response", retry=True)
            return bytes(content)
        except (OSError, http.client.HTTPException) as exc:
            raise FetchError(
                "timeout" if isinstance(exc, TimeoutError) else "network_error", retry=True
            ) from None
        finally:
            conn.close()
