from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Company, ScrapeResult


class BaseScraper(ABC):
    scraper_type = "base"

    @abstractmethod
    def can_handle(self, url: str) -> bool: ...

    @abstractmethod
    def fetch_jobs(self, company: Company) -> ScrapeResult: ...
