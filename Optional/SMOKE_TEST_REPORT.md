# CareerPath ATS Smoke Test Report

Date: 2026-07-10

## Environment

- OS shell: Windows PowerShell
- Python: 3.11.1 from `.venv`
- Flask entry point: `wsgi.py`
- Canonical database: `instance/career.db`
- Legacy database still present: `database.db` in project root, retained to avoid accidental data loss.
- Playwright: not installed in the current virtual environment, so browser-level Playwright automation was not executed.

## Commands Run

```powershell
.\.venv\Scripts\python.exe -m flask db current
.\.venv\Scripts\python.exe -m flask db upgrade
.\.venv\Scripts\python.exe -m flask routes
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
.\.venv\Scripts\python.exe -m ruff check app tests config.py
.\.venv\Scripts\python.exe -m bandit -r app
.\.venv\Scripts\python.exe -m pip_audit
.\.venv\Scripts\python.exe -m compileall app tests
```

## Results

- Database migration state: `0005_chat_archive_health (head)`
- Flask routes: 35 routes registered successfully.
- Unit/integration tests: `20 passed`
- Coverage: `79%`
- Ruff: `All checks passed`
- Bandit: `No issues identified`
- pip-audit: `No known vulnerabilities found`
- Compile check: passed for `app` and `tests`

## End-To-End Smoke Coverage

The Flask test client smoke covered:

- Anonymous landing page and authenticated dashboard redirects
- Register, login, logout
- Sidebar GET pages for dashboard, career, ATS, growth tools, chat, analytics, profile, and privacy
- Career assessment submit and result flow
- ATS PDF upload, PDF parsing, scan persistence, result page, and PDF report download
- AI roadmap creation, progress update, task completion, and regeneration/archive flow
- Learning Hub seed, filters, bookmark, start, progress, complete, open tracking, and unbookmark actions
- Resume Builder save, score, preview, and PDF download
- Interview Prep start, answer submission, and report
- Mock Interview start, answer submission, and report
- Career chatbot message, archive, and delete
- Analytics dashboard
- Profile update
- Admin privacy gate: normal user receives `403`; configured admin user can access aggregate dashboard

## Defects Found And Fixed

- Fixed admin allowlist configuration so `/admin/` reads `ADMIN_EMAILS` from Flask app config, with support for string or iterable values. This keeps environment-based production behavior while allowing test/config-driven validation.
- Repaired the local virtualenv dependency metadata for `python-dotenv` and verified the installed audited version is no longer vulnerable.

## Notes

- Uploaded private resumes remain outside static assets under `uploads`.
- Admin dashboard remains aggregate-only and does not expose passwords, password hashes, uploaded resumes, private conversations, or sensitive personal content.
- The current smoke uses Flask's test client, not Playwright, because Playwright is not installed in this environment.
