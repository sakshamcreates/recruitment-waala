"""Bounded child process for text-only PDF extraction."""

import io
import resource
import sys

from pypdf import PdfReader


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (3, 4))
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (384 * 1024**2, 384 * 1024**2))
    body = sys.stdin.buffer.read(2_000_001)
    if not body.startswith(b"%PDF-") or len(body) > 2_000_000:
        return 2
    reader = PdfReader(io.BytesIO(body), strict=True)
    if reader.is_encrypted or not 1 <= len(reader.pages) <= 30:
        return 2
    text = "\n".join((page.extract_text() or "")[:20000] for page in reader.pages)
    print(text[:50000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
