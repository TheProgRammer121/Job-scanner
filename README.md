# Career Page Monitor

A personal, zero-cost job monitor built around conservative public-page checks. It stores job history in SQLite, identifies newly seen jobs, ranks them against your preferences, and can email a daily summary when SMTP credentials are set.

## Quick start

1. Install Python 3.12+ and create a virtual environment.
2. Install dependencies: `python -m pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and, if desired, configure SMTP.
4. Edit `companies.json` with the careers pages to monitor.
5. Run `python main.py`.

The included NVIDIA entry uses the URL supplied for this project. The first run creates the local `data/job_monitor.db` database. Use `--send-baseline` only if you want an email containing every opening discovered on that first run.

## Commands

```text
python main.py                 Check all enabled companies
python main.py --company NVIDIA
python main.py --no-email      Store results without sending email
python main.py --send-baseline Include first-run jobs in the email
```

## Important behaviour

- A 403, CAPTCHA, timeout, parsing error, or suspicious empty result is logged as a failed check—not as “no jobs”.
- Jobs are matched by official ID, then URL, then a deterministic fingerprint.
- HTML is not stored or rendered; only normalized text fields are persisted.
- The generic scraper supports JSON-LD and ordinary job-card markup. JavaScript listings that do not expose jobs in the HTTP response are reported as needing a browser/API adapter rather than guessed.

## Automation

The GitHub Actions workflow in `.github/workflows/daily_monitor.yml` runs at 08:00 India Standard Time (02:30 UTC) and also supports manual runs. Add the same `.env` values as repository secrets before enabling email in Actions.
