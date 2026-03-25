# KnowledgeBase AI

Production-ready MVP for a self-hosted internal knowledge base with AI instant answers and source citations.

## Full Documentation
For complete application documentation (architecture, all UI functions, API reference, RBAC, config, operations, and troubleshooting), see:
- [APP_DOKUMENTATION.md](APP_DOKUMENTATION.md)

For detailed installation/handover instructions (including external license-server setup), see:
- [How_To_Install.md](How_To_Install.md)

## Stack
- Frontend: Next.js 14 (App Router), TypeScript, TailwindCSS, Recharts
- Backend: FastAPI, SQLAlchemy, Alembic, Celery, Redis
- DB: PostgreSQL + pgvector
- AI Providers:
  - OpenAI (active)
  - Ollama (runtime-switchable)
  - Local provider placeholder (`local`) for development fallback

## Architecture
- `frontend` calls `api` using cookie auth.
- `api` handles auth, RBAC, documents, chat, dashboard and queues ingestion jobs.
- `worker` runs Celery ingestion tasks (parse/chunk/embed/store).
- `postgres` stores metadata, chat logs, and vectors.
- `redis` is broker/result backend + rate-limit store.
- Uploaded files are persisted in Docker volume `uploads_data` mounted to `/data/uploads`.
- Application support logs are persisted in Docker volume `app_logs_data` mounted to `/data/logs` for bounded admin export.

## Repo Structure
- `backend/` FastAPI app, migrations, Celery tasks, tests
- `frontend/` Next.js UI pages and components
- `docker-compose.yml` local runtime

## External License Server
This repository contains the main KnowledgeBase AI application only.

The external license server is maintained separately and is not bundled into this repository:
- expected local path: `external/kbai-license-server`
- separate source repository: `git@github.com:Tim-M-83/kbai-license-server.git`

If you clone this repository on a new machine, fetch or place the external license server separately when you need the production billing/license-server stack.

## Quick Start
For the fastest customer install flow, host the rendered installer scripts from `quickstart/` on your marketing website and point customers to:

macOS/Linux:
```bash
curl -fsSL https://knowledgebaseai.de/knowledgebase-ai/install.sh | bash
```

Windows PowerShell:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://knowledgebaseai.de/knowledgebase-ai/install.ps1 | iex"
```

What the one-line installer does:
- checks that Docker and `docker compose` are available and running
- verifies that ports `3000`, `8000`, `5432`, and `6379` are free
- downloads the latest stable GitHub release asset, not `main`
- creates `.env` with secure defaults and starts the Docker stack
- prints the bootstrap admin credentials from the API logs when available

Before publishing the one-line installer publicly:
- make `Tim-M-83/knowledgebase-ai` public so anonymous release downloads work
- create a GitHub release with `knowledgebase-ai.tar.gz` and `knowledgebase-ai.zip`
- render hosted installers with `QUICKSTART_LICENSE_SERVER_ADMIN_TOKEN`
- host the rendered files at `https://knowledgebaseai.de/knowledgebase-ai/install.sh` and `https://knowledgebaseai.de/knowledgebase-ai/install.ps1`

Security note:
- the quick-start flow intentionally distributes a shared `LICENSE_SERVER_ADMIN_TOKEN` inside the public installer so checkout works immediately after installation
- this is convenient for onboarding, but it means the current `/billing/*` protection is operationally convenient rather than secret

## Manual Setup
1. Copy env template:
   ```bash
   cp .env.example .env
   ```
2. Add your `OPENAI_API_KEY` in `.env` (for OpenAI mode), or set it later in the Settings page.
3. Start all services:
   ```bash
   docker compose up --build
   ```
4. API available at `http://localhost:8000`, frontend at `http://localhost:3000`.

## Migrations
Migrations run automatically when the API container starts.

Manual migration command:
```bash
docker compose exec api alembic upgrade head
```

## Bootstrap First Admin
On a fresh installation, the API creates a one-time bootstrap admin automatically.
Read the credentials from the API logs:
```bash
docker compose logs api
```
- Bootstrap email: `admin@local`
- Bootstrap password: generated randomly per installation and printed only once at first bootstrap
- Sign in immediately, then go to `Settings` and complete the mandatory credential change flow.
- `seed_admin` remains available as an emergency/manual fallback tool:
```bash
docker compose exec api python -m app.scripts.seed_admin --email admin@example.com --password ChangeMe123!
```

## Provider Toggle
Startup defaults in `.env`:
```env
LLM_PROVIDER=openai
EMBEDDINGS_PROVIDER=openai
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_CHAT_MODEL=llama3.1:8b
OLLAMA_EMBEDDINGS_MODEL=nomic-embed-text
```
Runtime switching (no restart) is available in **Settings** for admins:
- Choose provider: `openai` or `ollama` (LLM + embeddings switch together)
- Save OpenAI key without losing it when switching away
- Test OpenAI and Ollama connectivity from the UI
- Save is allowed with warning when provider checks fail
- Admin-only inline setup help includes official links for OpenAI API key creation and Ollama installation/model library

Notes:
- Use `http://host.docker.internal:11434` for Ollama when app runs in Docker and Ollama runs on host.
- The local stub providers remain available as internal fallback only.

## Main Features
- Email/password auth with roles: `admin`, `editor`, `viewer`
- Self-service account security in Settings (each authenticated user can update own email/password)
- Automatic bootstrap admin on fresh installs with forced first-login credential change
- External license-server monetization flow with hosted Polar checkout, pasted Polar license key activation, and local grace-period enforcement
- Strict RBAC checks server-side
- Document upload + async ingestion (PDF/TXT/CSV)
- Chunking with overlap + vector indexing (pgvector)
- Chat with streaming responses and citations
- Structured Markdown answers for better readability
- Sources panel (doc/page or csv rows + snippet)
- Session history per user
- Feedback (thumbs up/down + comment)
- Per-answer print action in chat
- Dashboard KPIs, usage charts, and knowledge gaps list
- Admin pages for users/tags/departments

## API Surface
- Auth: `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `PUT /auth/me/credentials`
- License: `GET /license/status`, `POST /license/checkout`, `POST /license/activate` (accepts pasted Polar `license_key`), `POST /license/validate`, `POST /license/deactivate`
- Users: `GET/POST/PUT/DELETE /users`
- Documents: `POST /documents/upload`, `GET /documents`, `GET /documents/{id}`, `PUT /documents/{id}/metadata`, `DELETE /documents/{id}`, `POST /documents/{id}/index`, `POST /documents/{id}/reingest`
- Chat: `POST /chat/sessions`, `GET /chat/sessions`, `DELETE /chat/sessions`, `GET /chat/sessions/{id}`, `POST /chat/ask` (SSE), `POST /chat/feedback`
- Dashboard: `GET /dashboard/kpis`, `GET /dashboard/charts`, `GET /dashboard/gaps`, `DELETE /dashboard/gaps` (admin only)
- Settings:
  - `GET /settings/data`, `PUT /settings/data` (admin write)
  - `GET /settings/providers`, `PUT /settings/providers` (runtime provider + OpenAI/Ollama config)
  - `POST /settings/providers/test-openai` (tests OpenAI Responses + Embeddings endpoints)
  - `POST /settings/providers/test-ollama` (tests Ollama chat + embeddings endpoints)
  - `GET /settings/log-export` (admin-only bounded ZIP export of recent API + worker support logs)
- Health: `GET /health`

## UI Layout
- Login page
- Global app header with Logout action for authenticated users
- Dashboard: KPI cards + charts + gaps
- Documents: upload dialog + status table
- Document detail: metadata, chunk count, ingestion error status
- Inline creation of new tags/departments in document upload and detail flows (admin/editor)
- Chat: sessions panel, streaming conversation area, structured answer rendering, per-answer print, source panel, filters
  - Sources are persisted per assistant answer and restored when reopening sessions
- Admin: users/tags/departments CRUD
- Settings: provider/model display + connection test
  - Runtime provider selector (OpenAI/Ollama), Ollama URL/model config, OpenAI key update
  - Admin-only support diagnostics export for recent API + worker events/errors

## Tests
Backend unit tests:
```bash
docker compose exec api pytest -q
```
Included tests:
- Chunking overlap/metadata
- RBAC visibility checks
- Celery task registration
- Retrieval ready-document filtering
- Chat low-confidence warning logic

## Ingestion Operations
Check that the worker has the ingestion task registered:
```bash
docker compose logs worker | grep ingest_document
```

Re-index a specific document manually:
- Use the `Index` button in the Documents list or Document detail page (requires authenticated admin/editor session).

Expected document status flow:
- `uploaded` -> queued for indexing
- `processing` -> currently indexing
- `ready` -> indexed and searchable
- `failed` -> indexing failed (see `error_text` in document detail)

## Troubleshooting
- Document stays in `uploaded` and never reaches `ready`:
  - Check worker is running: `docker compose ps`
  - Check worker task registration: `docker compose logs worker | grep ingest_document`
  - Check Redis health: `docker compose ps redis`
- Chat says there are not enough reliable sources:
  - Ensure at least one relevant document is `ready`
  - Use the document `Index` button to re-run ingestion
  - Verify sources panel and chunk count on document detail page

## Security Notes
- JWT in httpOnly cookie
- Double-submit CSRF token check on mutating endpoints
- OpenAI API key can be set live via Settings and is encrypted at rest
- Provider selection (OpenAI/Ollama) is global runtime app setting (single-tenant)
- Support log export is admin-only, time-bounded, line-bounded, and intended for troubleshooting without exporting secrets or document/chat contents
- Upload MIME/extension + max-size checks
- Chat endpoint rate-limited via Redis

## MVP Limits
- No SSO
- No OCR
- No DOCX parsing yet
- No multi-tenant isolation
