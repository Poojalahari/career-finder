# CareerPath ATS

CareerPath ATS is a secure Flask application for career recommendations and ATS-style resume scanning. It replaces the original prototype with an application-factory structure, SQLAlchemy models, Flask-Login authentication, CSRF-protected forms, private PDF storage, explainable scoring, migrations, tests, and production deployment files.

## Features

- Supabase registration and authentication, remember-me sessions, POST logout, and duplicate-account prevention.
- User dashboard with real per-user scan and assessment statistics.
- Explainable career recommendation engine backed by `Backend/app/career/career_taxonomy.json`.
- PDF-only ATS scanner with private UUID storage, SHA-256 checksums, text extraction, job-description keyword matching, scan history, deletion, and downloadable PDF reports.
- AI Career Roadmap, learning recommendations, ATS resume builder, combined Interview Prep with practice and mock modes, and private career chatbot.
- Dashboard analytics for career compatibility, learning progress, ATS trends, interview performance, and skill progress.
- Privacy-first admin portal with aggregate-only metrics. Admins cannot access passwords, password hashes, uploaded resumes, private conversations, or sensitive personal information.
- Error pages, `/health`, security headers, rate limiting, Docker, Gunicorn, and Waitress documentation.

## Architecture

The repository has three project folders: `frontend` contains templates and browser assets, `Backend` contains the Flask application and database migrations, and `Optional` contains local tests and development artifacts that are not required in a production image. The app uses `create_app()` in `Backend/app/__init__.py`, Blueprints for each feature, SQLAlchemy models, and testable service modules.

## Windows PowerShell Local Setup

Requirements: Python 3.11 and Node.js 18 or newer. From the repository root (`C:\Users\DELL\OneDrive\career-ml-system`), the shortest setup is:

```powershell
npm run dev
```

This command finds or creates the Python environment, installs missing backend dependencies, applies database migrations, and serves the complete application at `http://127.0.0.1:5000`. The browser UI remains in `frontend`; npm is the development command while Flask remains the application server.

There is no separate React/Vite frontend process or frontend API origin. Flask renders `frontend/templates` and serves `frontend/static`, so the backend and frontend URL are both `http://127.0.0.1:5000` and CORS is not required.

Manual setup is also supported:

```powershell
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r Backend/requirements.txt
Copy-Item .env.example .env
$env:FLASK_APP = "Backend/wsgi.py"
flask --app Backend/wsgi.py db upgrade -d Backend/migrations
flask --app Backend/wsgi.py run
```

The compatibility command below also starts the same Flask application without creating a second app:

```powershell
python app.py
```

For a fresh checkout, use these exact commands:

```powershell
Set-Location "C:\Users\DELL\OneDrive\career-ml-system"
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r Backend\requirements.txt
npm install
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -m flask --app Backend\wsgi.py db upgrade -d Backend\migrations
npm run dev
```

Backend-only command:

```powershell
python -m flask --app Backend\wsgi.py run --debug
```

The frontend is server-rendered and has no standalone command. Use `npm run dev` to serve both layers. Production asset validation and tests:

```powershell
npm run build
python -m pytest -v
python -m ruff check Backend Optional\tests app.py
```

Troubleshooting:

```powershell
Get-Command python,node,npm
$env:Path = "C:\Program Files\nodejs;$env:Path"
python -m flask --app Backend\wsgi.py routes
Invoke-RestMethod http://127.0.0.1:5000/health
```

## Local Setup: Linux/macOS

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r Backend/requirements.txt
cp .env.example .env
export FLASK_APP=Backend/wsgi.py
flask --app Backend/wsgi.py db upgrade -d Backend/migrations
flask --app Backend/wsgi.py run
```

## Environment Variables

Use `.env.example` as the safe template and configure real values in `.env` or the hosting provider, never in Git. Set the Supabase URL, publishable key, server-only secret key, and the transaction-pooler `DATABASE_URL` from **Project Settings > Database > Connect**. Old `SUPABASE_ANON_KEY` and `SUPABASE_SERVICE_ROLE_KEY` names remain supported. Tokens are stored in Flask's server-side session; set `SESSION_REDIS_URL` in multi-worker production deployments.

With **Confirm Email** enabled, registration reports that the account was created and the verification link was sent. The default Supabase confirmation link redirects to `/auth/callback` with an implicit session, which the callback exchanges for the server-side Flask session before opening `/dashboard`. For a server-token callback instead, set the Confirm signup email link to `{{ .RedirectTo }}?token_hash={{ .TokenHash }}&type=email`. Allow `http://127.0.0.1:5000/auth/callback` in Redirect URLs. Configure the recovery email link as `{{ .RedirectTo }}?token_hash={{ .TokenHash }}&type=recovery`. Run the Flask migrations, then execute `supabase/schema.sql` in the Supabase SQL editor to install the profile trigger, RLS, and private `career-documents` bucket policies.

## Render Production

Create the service from the root `render.yaml` Blueprint so Render builds `Backend/Dockerfile` with the repository root as its Docker context. The container applies all Flask migrations before starting Gunicorn on Render's dynamic `PORT`; `package.json` is only a local development launcher.

Configure every `sync: false` environment variable in the Render dashboard. For the production Supabase project, enable email/password signup and set:

- Site URL: `https://career-finder-a4dh.onrender.com`
- Allowed redirect URL: `https://career-finder-a4dh.onrender.com/auth/callback`
- `SUPABASE_EMAIL_REDIRECT_URL`: `https://career-finder-a4dh.onrender.com/auth/callback`

The database URL must be the Supabase PostgreSQL connection or transaction-pooler URL supported by psycopg. Production startup intentionally fails before serving traffic when required authentication, callback, database, storage, admin, or secret-key configuration is missing.

## Database

Migration `0009_uuid_profiles_storage` non-destructively maps legacy integer users to UUID profiles, retains legacy ownership columns for audit, removes legacy password hashes, converts active ownership to UUID foreign keys, and adds Supabase storage paths and ATS status constraints.

Additional migrations add `learning_progress`, `resume_documents`, `interview_sessions`, `chat_conversations`, and `chat_messages`.

Supabase Auth is the only password authority. Legacy local accounts must register through Supabase before signing in.

## ATS Scoring

When a job description is present, the 100-point rubric is: keyword match 35, experience 20, section completeness 15, quantified achievements 10, education/certifications 8, readability 7, contact 5.

Without a job description, the 100-point rubric is: section completeness 25, skills 20, experience 20, achievements 15, readability 10, education/certifications 5, contact 5.

Scores are advisory compatibility signals, not guarantees of acceptance by any employer or ATS vendor.

## PDF Restrictions and Privacy

Only one PDF is accepted per scan. The server validates extension, MIME type, `%PDF-` signature, non-empty body, parseability, encryption, page count, and size. Fake renamed PDFs, empty files, corrupt PDFs, non-PDF MIME types, excessive pages, and image-only PDFs without extractable text are rejected. Full resume text is analyzed in memory and is not stored by default.

Completed resumes are stored in the private Supabase Storage bucket at `{user_id}/resumes/{uuid}.pdf`. Only metadata and analysis results are stored in PostgreSQL. Authorized downloads use five-minute signed URLs, and deletion removes both the object and database row.

## API and Route Reference

- `GET /health`: JSON health check.
- `/career/*`: career assessment, result, and history.
- `/ats/*`: PDF scanner, scan history, report download, deletion.
- `/growth/roadmap`: personalized roadmap and progress tracking.
- `/growth/learning`: learning resources.
- `/growth/resume-builder`: resume creation, score, preview, PDF export.
- `/growth/interview-prep`: combined practice questions, mock interview mode, and interview history. Legacy `/growth/mock-interview` redirects to the mock tab for compatibility.
- `/chat/`: private AI career chatbot and conversation history.
- `/analytics/`: user analytics dashboard.
- `/admin/`: aggregate portal restricted to `admin` and `super_admin` roles. `ADMIN_EMAILS` is used only to bootstrap the first super administrator.

## Admin Privacy Guarantees

The admin portal shows aggregate counts and trends only: total users, active users, career statistics, popular careers, ATS analytics, interview analytics, user growth, learning progress, feature usage, taxonomy counts, reports, and system health. It does not expose password hashes, uploaded resume files, private chat message content, or sensitive user profile data.

## Production

Gunicorn on Linux:

```bash
export FLASK_ENV=production
export FLASK_SECRET_KEY="change-me"
export FLASK_APP=Backend/wsgi.py
flask --app Backend/wsgi.py db upgrade -d Backend/migrations
gunicorn --chdir Backend -b 0.0.0.0:8000 wsgi:app
```

Waitress on Windows:

```powershell
$env:FLASK_ENV = "production"
$env:FLASK_SECRET_KEY = "change-me"
$env:FLASK_APP = "Backend/wsgi.py"
flask --app Backend/wsgi.py db upgrade -d Backend/migrations
Push-Location Backend
python -m waitress --host=0.0.0.0 --port=5000 wsgi:app
Pop-Location
```

Docker:

```powershell
$env:FLASK_SECRET_KEY = "change-me"
docker compose up --build
```

## Quality Commands

```powershell
py -3.11 -m compileall .
py -3.11 -m ruff check Backend Optional/tests
py -3.11 -m pytest -q
py -3.11 -m pytest --cov=Backend/app --cov-report=term-missing
py -3.11 -m bandit -r Backend/app
py -3.11 -m pip_audit
```

## OCR Behavior

OCR is disabled by default. Image-only/scanned PDFs return a clear validation error instead of pretending to analyze unavailable text. If OCR is added later, keep it behind `OCR_ENABLED` and document the system dependency.

## Known Limitations

The ATS scanner is deterministic and explainable, but it is not a vendor-specific ATS emulator. Spelling detection is intentionally conservative to avoid unreliable false positives.
