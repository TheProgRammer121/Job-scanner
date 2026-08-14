from __future__ import annotations

from dataclasses import dataclass

from .models import JobPosting
from .normalize import normalized_text

POSITIVE = {"rtl design": 10, "design verification": 10, "systemverilog": 8, "verification engineer": 8, "digital design": 8, "rtl": 8, "uvm": 8, "verilog": 6, "microarchitecture": 6, "asic": 5, "fpga": 5, "risc-v": 5, "soc": 4, "hardware engineer": 3}
ENTRY_LEVEL = {"new graduate": 10, "entry level": 10, "fresher": 10, "intern": 8, "internship": 8, "graduate": 8, "engineer i": 6, "associate engineer": 6, "0-2 years": 5}
NEGATIVE = {"director": -20, "principal": -15, "manager": -15, "staff": -10, "lead": -8, "senior": -6, "8+ years": -20, "10+ years": -25}


@dataclass(frozen=True)
class Score:
    value: int
    tier: str
    matched_terms: tuple[str, ...]


def score_job(job: JobPosting, preferred_keywords: list[str], preferred_locations: list[str]) -> Score:
    text = normalized_text(" ".join((job.title, job.location, job.description)))
    location = normalized_text(job.location)
    terms: list[str] = []
    value = 0
    for term, weight in {**POSITIVE, **ENTRY_LEVEL, **NEGATIVE}.items():
        if normalized_text(term) in text:
            value += weight
            terms.append(term)
    for term in preferred_keywords:
        normal = normalized_text(term)
        if normal and normal in text and normal not in terms:
            value += 3
            terms.append(term)
    if preferred_locations:
        matches = [item for item in preferred_locations if normalized_text(item) in location]
        if matches:
            value += 3
            terms.extend(matches)
        else:
            value -= 3
    tier = "high" if value >= 15 else "possible" if value >= 8 else "low" if value >= 1 else "hidden"
    return Score(value, tier, tuple(dict.fromkeys(terms)))
