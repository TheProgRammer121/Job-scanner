from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Company:
    id: int | None
    name: str
    url: str
    enabled: bool = True
    priority: int = 1


@dataclass(frozen=True)
class JobPosting:
    title: str
    location: str
    url: str
    external_id: str | None = None
    description: str = ""
    posted_date: str | None = None


@dataclass(frozen=True)
class ScrapeResult:
    status: Literal["success", "blocked", "timeout", "network_error", "parser_error", "suspicious"]
    jobs: list[JobPosting] = field(default_factory=list)
    scraper_type: str = "generic"
    response_code: int | None = None
    content_hash: str | None = None
    error_message: str | None = None

    @property
    def successful(self) -> bool:
        return self.status == "success"
