from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit


def normalized_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "").lower().strip()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s+.-]", " ", text)).strip()


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))


def job_identity(company_name: str, external_id: str | None, url: str, title: str, location: str) -> str:
    if external_id:
        seed = f"id:{normalized_text(external_id)}"
    elif url:
        seed = f"url:{canonical_url(url)}"
    else:
        seed = f"fingerprint:{normalized_text(company_name)}|{normalized_text(title)}|{normalized_text(location)}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def content_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
