from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from .models import JobPosting
from .scoring import Score


def send_summary(entries: list[tuple[str, JobPosting, Score]], failures: list[tuple[str, str]]) -> bool:
    recipient, username, password = os.getenv("NOTIFY_TO"), os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD")
    if not recipient or not username or not password:
        return False
    lines = ["Career Page Monitor daily summary", ""]
    for company, job, score in entries:
        lines += [f"[{score.tier.upper()} | {score.value}] {company}: {job.title}", f"{job.location} — {job.url}", ""]
    for company, reason in failures:
        lines += [f"MANUAL CHECK REQUIRED — {company}", reason, ""]
    message = EmailMessage()
    message["Subject"] = f"Job Watch — {len(entries)} new relevant jobs"
    message["From"] = username
    message["To"] = recipient
    message.set_content("\n".join(lines))
    with smtplib.SMTP_SSL(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "465"))) as server:
        server.login(username, password)
        server.send_message(message)
    return True
