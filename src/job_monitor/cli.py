from __future__ import annotations

import argparse
import os

from .config import list_value, load_companies, load_dotenv
from .notifier import send_summary
from .scoring import score_job
from .scrapers import ScraperManager
from .store import create_store


def main() -> int:
    parser = argparse.ArgumentParser(description="Check saved public career pages for new jobs.")
    parser.add_argument("--company", help="Check one company by exact name")
    parser.add_argument("--no-email", action="store_true", help="Never send an email")
    parser.add_argument("--send-baseline", action="store_true", help="Send jobs found for the first time")
    arguments = parser.parse_args()
    load_dotenv()
    database, manager = create_store(), ScraperManager()
    preferences = (list_value("PREFERRED_KEYWORDS"), list_value("PREFERRED_LOCATIONS"))
    relevant, failures = [], []
    try:
        for configured in load_companies():
            database.upsert_company(configured)
        companies = [company for company in database.list_companies() if not arguments.company or company.name == arguments.company]
        if arguments.company and not companies:
            parser.error(f"No enabled company named {arguments.company!r} in companies.json")
        for configured in companies:
            company = configured
            result = manager.fetch(company)
            scored = [(job, score_job(job, *preferences)) for job in result.jobs]
            stored = database.persist(company, result, scored)
            print(f"{company.name}: {result.status}; jobs={len(result.jobs)}; new={len(stored.new_jobs)}; scraper={result.scraper_type}")
            if result.error_message:
                print(f"  {result.error_message}")
            if not result.successful:
                failures.append((company.name, result.error_message or result.status))
                continue
            if not stored.baseline or arguments.send_baseline or os.getenv("SEND_BASELINE_NOTIFICATIONS", "false").lower() == "true":
                for job, score in scored:
                    if job in stored.new_jobs and score.tier != "hidden":
                        relevant.append((company.name, job, score))
        if not arguments.no_email and (relevant or failures):
            if send_summary(relevant, failures):
                print("Daily email sent.")
            else:
                print("Email not configured; summary retained in the database and console output.")
    finally:
        database.close()
    return 0
