from __future__ import annotations

import json
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..models import Company, JobPosting, ScrapeResult
from ..normalize import content_hash, normalized_text
from .base import BaseScraper


class GenericScraper(BaseScraper):
    """Extract public JSON-LD first, then conventional job-card HTML."""

    scraper_type = "generic_http"
    headers = {"User-Agent": "CareerPageMonitor/1.0 (personal low-frequency monitor)"}

    def can_handle(self, url: str) -> bool:
        return url.startswith(("https://", "http://"))

    def fetch_jobs(self, company: Company) -> ScrapeResult:
        try:
            response = requests.get(company.url, headers=self.headers, timeout=30)
        except requests.Timeout:
            return ScrapeResult(status="timeout", scraper_type=self.scraper_type, error_message="Request timed out")
        except requests.RequestException as error:
            return ScrapeResult(status="network_error", scraper_type=self.scraper_type, error_message=str(error))
        body, digest, lowered = response.text, content_hash(response.text), response.text.lower()
        challenge_markers = ("cf-chl-", "captcha challenge", "captcha required", "verify you are human")
        if response.status_code in {401, 403, 429} or any(token in lowered for token in challenge_markers):
            return ScrapeResult(status="blocked", scraper_type=self.scraper_type, response_code=response.status_code, content_hash=digest, error_message="Site rejected or challenged the request")
        if response.status_code >= 400:
            return ScrapeResult(status="network_error", scraper_type=self.scraper_type, response_code=response.status_code, content_hash=digest, error_message=f"HTTP {response.status_code}")
        try:
            jobs = self._json_ld_jobs(body, company.url) or self._job_card_jobs(body, company.url)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            return ScrapeResult(status="parser_error", scraper_type=self.scraper_type, response_code=response.status_code, content_hash=digest, error_message=str(error))
        return ScrapeResult(status="success" if jobs else "suspicious", jobs=jobs, scraper_type=self.scraper_type, response_code=response.status_code, content_hash=digest, error_message=None if jobs else "No public job data found; configure a site-specific API or browser adapter")

    def _json_ld_jobs(self, html: str, page_url: str) -> list[JobPosting]:
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[JobPosting] = []
        for tag in soup.select('script[type="application/ld+json"]'):
            if not tag.string:
                continue
            payload = json.loads(tag.string)
            for item in self._walk_json(payload):
                if str(item.get("@type", "")).lower() != "jobposting":
                    continue
                title = item.get("title", "").strip()
                if not title:
                    continue
                identifier = item.get("identifier") or {}
                external_id = identifier.get("value") if isinstance(identifier, dict) else str(identifier)
                jobs.append(JobPosting(title=title, location=self._location(item.get("jobLocation")), url=urljoin(page_url, item.get("url") or page_url), external_id=external_id or None, description=BeautifulSoup(item.get("description", ""), "html.parser").get_text(" ", strip=True), posted_date=item.get("datePosted")))
        return self._dedupe(jobs)

    def _job_card_jobs(self, html: str, page_url: str) -> list[JobPosting]:
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[JobPosting] = []
        for link in soup.select('a[href*="job"], a[href*="career"]'):
            title = link.get_text(" ", strip=True)
            if not title or len(title) > 180 or normalized_text(title) in {"apply", "careers", "search jobs", "view job"}:
                continue
            container = link.find_parent(["article", "li", "div"])
            text = container.get_text(" ", strip=True) if container else title
            jobs.append(JobPosting(title=title, location=self._guess_location(text.replace(title, "", 1)), url=urljoin(page_url, link.get("href", ""))))
        return self._dedupe(jobs)

    @staticmethod
    def _walk_json(payload: object):
        if isinstance(payload, dict):
            yield payload
            for value in payload.values():
                yield from GenericScraper._walk_json(value)
        elif isinstance(payload, list):
            for value in payload:
                yield from GenericScraper._walk_json(value)

    @staticmethod
    def _location(value: object) -> str:
        values, parts = value if isinstance(value, list) else [value], []
        for entry in values:
            if isinstance(entry, dict):
                address = entry.get("address", entry)
                if isinstance(address, dict):
                    parts.append(", ".join(str(address.get(key, "")) for key in ("addressLocality", "addressRegion", "addressCountry") if address.get(key)))
        return " / ".join(filter(None, parts)) or "Unspecified"

    @staticmethod
    def _guess_location(text: str) -> str:
        for token in ("Bengaluru", "Bangalore", "Hyderabad", "Pune", "Chennai", "Noida", "Remote", "India"):
            if token.lower() in text.lower():
                return token
        return "Unspecified"

    @staticmethod
    def _dedupe(jobs: list[JobPosting]) -> list[JobPosting]:
        seen, output = set(), []
        for job in jobs:
            key = (normalized_text(job.title), job.url)
            if key not in seen:
                seen.add(key)
                output.append(job)
        return output
