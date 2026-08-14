import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from job_monitor.database import Database
from job_monitor.models import Company, JobPosting, ScrapeResult
from job_monitor.normalize import job_identity, normalized_text
from job_monitor.scoring import score_job


class CoreTests(unittest.TestCase):
    def test_normalization_is_stable(self):
        self.assertEqual(normalized_text(" RTL  Design—Engineer "), "rtl design engineer")

    def test_external_identifier_takes_priority(self):
        first = job_identity("NVIDIA", "JR100", "https://one", "Role A", "India")
        second = job_identity("NVIDIA", "jr100", "https://two", "Role B", "US")
        self.assertEqual(first, second)

    def test_relevance_and_seniority(self):
        job = JobPosting("Senior RTL Verification Engineer", "India, Bengaluru", "https://example.test", description="SystemVerilog and UVM")
        score = score_job(job, ["RTL"], ["Bengaluru"])
        self.assertGreaterEqual(score.value, 15)
        self.assertEqual(score.tier, "high")

    def test_second_persist_does_not_repeat_a_job(self):
        with TemporaryDirectory() as directory:
            database = Database(Path(directory) / "monitor.db")
            company = database.upsert_company(Company(None, "Example", "https://example.test/jobs"))
            job = JobPosting("RTL Engineer", "Bengaluru", "https://example.test/jobs/1", "JR1")
            result = ScrapeResult(status="success", jobs=[job])
            score = score_job(job, [], [])
            self.assertEqual(len(database.persist(company, result, [(job, score)]).new_jobs), 1)
            self.assertEqual(len(database.persist(company, result, [(job, score)]).new_jobs), 0)
            database.close()


if __name__ == "__main__":
    unittest.main()
