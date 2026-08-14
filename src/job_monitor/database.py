from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .models import Company, JobPosting, ScrapeResult, utc_now
from .normalize import job_identity
from .scoring import Score


@dataclass(frozen=True)
class PersistResult:
    new_jobs: list[JobPosting]
    baseline: bool


class Database:
    def __init__(self, path: str | Path = "data/job_monitor.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def close(self) -> None:
        self.connection.close()

    def _create_schema(self) -> None:
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
          id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, career_url TEXT NOT NULL,
          enabled INTEGER NOT NULL DEFAULT 1, priority INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_checked_at TEXT,
          last_successful_check TEXT, last_error TEXT
        );
        CREATE TABLE IF NOT EXISTS jobs (
          id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
          identity TEXT NOT NULL, external_job_id TEXT, title TEXT NOT NULL, location TEXT,
          job_url TEXT NOT NULL, description TEXT, date_posted TEXT, first_seen TEXT NOT NULL,
          last_seen TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active', relevance_score INTEGER NOT NULL,
          UNIQUE(company_id, identity)
        );
        CREATE TABLE IF NOT EXISTS company_checks (
          id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
          checked_at TEXT NOT NULL, status TEXT NOT NULL, jobs_found INTEGER NOT NULL,
          new_jobs_found INTEGER NOT NULL, response_code INTEGER, scraper_type TEXT,
          content_hash TEXT, error_message TEXT
        );
        """)
        self.connection.commit()

    def upsert_company(self, company: Company) -> Company:
        now = utc_now()
        self.connection.execute("""
          INSERT INTO companies (name, career_url, enabled, priority, created_at, updated_at)
          VALUES (?, ?, ?, ?, ?, ?)
          ON CONFLICT(name) DO UPDATE SET career_url=excluded.career_url, enabled=excluded.enabled,
          priority=excluded.priority, updated_at=excluded.updated_at
        """, (company.name, company.url, int(company.enabled), company.priority, now, now))
        self.connection.commit()
        row = self.connection.execute("SELECT id, name, career_url, enabled, priority FROM companies WHERE name=?", (company.name,)).fetchone()
        return Company(row["id"], row["name"], row["career_url"], bool(row["enabled"]), row["priority"])

    def list_companies(self) -> list[Company]:
        rows = self.connection.execute("SELECT id, name, career_url, enabled, priority FROM companies WHERE enabled=1 ORDER BY priority, name").fetchall()
        return [Company(row["id"], row["name"], row["career_url"], bool(row["enabled"]), row["priority"]) for row in rows]

    def persist(self, company: Company, result: ScrapeResult, scored: list[tuple[JobPosting, Score]]) -> PersistResult:
        now = utc_now()
        baseline = self.connection.execute("SELECT COUNT(*) FROM jobs WHERE company_id=?", (company.id,)).fetchone()[0] == 0
        new_jobs: list[JobPosting] = []
        if result.successful:
            for job, score in scored:
                identity = job_identity(company.name, job.external_id, job.url, job.title, job.location)
                known = self.connection.execute("SELECT id FROM jobs WHERE company_id=? AND identity=?", (company.id, identity)).fetchone()
                if known is None:
                    new_jobs.append(job)
                    self.connection.execute("""INSERT INTO jobs (company_id, identity, external_job_id, title, location, job_url, description, date_posted, first_seen, last_seen, relevance_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (company.id, identity, job.external_id, job.title, job.location, job.url, job.description, job.posted_date, now, now, score.value))
                else:
                    self.connection.execute("UPDATE jobs SET title=?, location=?, job_url=?, description=?, date_posted=?, last_seen=?, status='active', relevance_score=? WHERE id=?", (job.title, job.location, job.url, job.description, job.posted_date, now, score.value, known["id"]))
            self.connection.execute("UPDATE companies SET last_checked_at=?, last_successful_check=?, last_error=NULL WHERE id=?", (now, now, company.id))
        else:
            self.connection.execute("UPDATE companies SET last_checked_at=?, last_error=? WHERE id=?", (now, result.error_message, company.id))
        self.connection.execute("""INSERT INTO company_checks (company_id, checked_at, status, jobs_found, new_jobs_found, response_code, scraper_type, content_hash, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (company.id, now, result.status, len(result.jobs), len(new_jobs), result.response_code, result.scraper_type, result.content_hash, result.error_message))
        self.connection.commit()
        return PersistResult(new_jobs, baseline)
