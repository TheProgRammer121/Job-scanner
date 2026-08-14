from __future__ import annotations

from dataclasses import dataclass

import requests

from .database import PersistResult
from .models import Company, JobPosting, ScrapeResult, utc_now
from .normalize import job_identity
from .scoring import Score


class SupabaseError(RuntimeError):
    pass


class SupabaseDatabase:
    """Small server-side PostgREST client; no browser-accessible keys involved."""

    def __init__(self, url: str, service_role_key: str) -> None:
        self.base_url = url.rstrip("/") + "/rest/v1"
        self.headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation,resolution=merge",
        }

    def close(self) -> None:
        return None

    def _request(self, method: str, resource: str, **kwargs):
        response = requests.request(method, f"{self.base_url}/{resource.lstrip('/')}", headers=self.headers, timeout=30, **kwargs)
        if response.status_code >= 400:
            raise SupabaseError(f"Supabase {response.status_code}: {response.text[:300]}")
        return response.json() if response.content else None

    def upsert_company(self, company: Company) -> Company:
        now = utc_now()
        rows = self._request("POST", "companies?on_conflict=name", json={
            "name": company.name, "career_url": company.url, "enabled": company.enabled,
            "priority": company.priority, "created_at": now, "updated_at": now,
        })
        row = rows[0]
        return Company(row["id"], row["name"], row["career_url"], row["enabled"], row["priority"])

    def list_companies(self) -> list[Company]:
        rows = self._request("GET", "companies?enabled=eq.true&select=id,name,career_url,enabled,priority&order=priority.asc,name.asc")
        return [Company(row["id"], row["name"], row["career_url"], row["enabled"], row["priority"]) for row in rows]

    def persist(self, company: Company, result: ScrapeResult, scored: list[tuple[JobPosting, Score]]) -> PersistResult:
        known = self._request("GET", f"jobs?company_id=eq.{company.id}&select=id,identity") if result.successful else []
        existing = {row["identity"]: row["id"] for row in known}
        baseline = not existing
        now, new_jobs = utc_now(), []
        if result.successful:
            new_rows = []
            for job, score in scored:
                identity = job_identity(company.name, job.external_id, job.url, job.title, job.location)
                if identity not in existing:
                    new_jobs.append(job)
                    new_rows.append({"company_id": company.id, "identity": identity, "external_job_id": job.external_id,
                    "title": job.title, "location": job.location, "job_url": job.url, "description": job.description,
                    "date_posted": job.posted_date, "first_seen": now, "last_seen": now, "status": "active", "relevance_score": score.value})
                else:
                    self._request("PATCH", f"jobs?id=eq.{existing[identity]}", json={"external_job_id": job.external_id,
                        "title": job.title, "location": job.location, "job_url": job.url, "description": job.description,
                        "date_posted": job.posted_date, "last_seen": now, "status": "active", "relevance_score": score.value})
            if new_rows:
                self._request("POST", "jobs", json=new_rows)
            self._request("PATCH", f"companies?id=eq.{company.id}", json={"last_checked_at": now, "last_successful_check": now, "last_error": None})
        else:
            self._request("PATCH", f"companies?id=eq.{company.id}", json={"last_checked_at": now, "last_error": result.error_message})
        self._request("POST", "company_checks", json={"company_id": company.id, "checked_at": now, "status": result.status,
            "jobs_found": len(result.jobs), "new_jobs_found": len(new_jobs), "response_code": result.response_code,
            "scraper_type": result.scraper_type, "content_hash": result.content_hash, "error_message": result.error_message})
        return PersistResult(new_jobs, baseline)
