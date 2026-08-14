from __future__ import annotations

from ..models import Company, ScrapeResult
from .base import BaseScraper
from .generic import GenericScraper


class ScraperManager:
    def __init__(self, scrapers: list[BaseScraper] | None = None) -> None:
        self.scrapers = scrapers or [GenericScraper()]

    def fetch(self, company: Company) -> ScrapeResult:
        for scraper in self.scrapers:
            if scraper.can_handle(company.url):
                return scraper.fetch_jobs(company)
        return ScrapeResult(status="parser_error", error_message="No scraper supports this URL")
