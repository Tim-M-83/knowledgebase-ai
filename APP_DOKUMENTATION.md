# KnowledgeBase AI - Application Documentation

Comprehensive technical and functional documentation for the KnowledgeBase AI Docker application.

## Table of Contents
- [1. Product Overview](#1-product-overview)
- [2. Architecture and Data Flow](#2-architecture-and-data-flow)
- [3. Roles, Permissions, and Security Model](#3-roles-permissions-and-security-model)
- [4. UI Feature Reference](#4-ui-feature-reference)
- [5. API Reference](#5-api-reference)
- [6. Configuration and Environment Variables](#6-configuration-and-environment-variables)
- [7. Operations and Runtime Management](#7-operations-and-runtime-management)
- [8. Troubleshooting Guide](#8-troubleshooting-guide)
- [9. Security Notes](#9-security-notes)
- [10. Current Limits](#10-current-limits)

## 1. Product Overview
KnowledgeBase AI is a self-hosted internal knowledge platform that lets teams:
- Upload business documents (PDF, TXT, CSV).
- Ingest and vector-index content asynchronously.
- Ask AI questions with source citations.
- Manage users, tags, departments, folders, and runtime provider settings.
- Upload external documents in an isolated AI Document Summarizer workspace (PDF, TXT, CSV, DOCX).

### Core capabilities
- Email/password authentication with role-based access (`admin`, `editor`, `viewer`).
- Self-service account credential updates (own email/password) for all authenticated users.
- External license-server monetization with local activation, validation, and grace-period enforcement.
- Document ingestion pipeline with status tracking (`uploaded`, `processing`, `ready`, `failed`).
- AI Document Summarizer for external documents (summary + document-specific chat).
- Chat sessions with streaming answers and saved source references.
- Private personal notes per user (create, edit, delete).
- Dashboard KPIs, charts, and "knowledge gaps" analytics.
- Runtime switching between OpenAI and Ollama providers (single-tenant runtime setting).
- Admin-only support diagnostics export with bounded recent API and worker logs.

### Taxonomy defaults and delete behavior
- The application seeds default departments: `HR`, `Sales`, `Support`.
- Departments remain fully extendable (admins/editors can create additional ones).
- Deleting a department automatically unassigns linked users and documents (`department_id = null`).
- Global folders are available for internal document organization and are visible to all users.
- Deleting a folder automatically unassigns linked documents (`folder_id = null`).
- Tag deletion is managed in the admin taxonomy area and removes tag links from documents.

## 2. Architecture and Data Flow
### 2.1 Services (Docker)
- `frontend`: Next.js UI (`http://localhost:3000`).
- `api`: FastAPI backend (`http://localhost:8000`).
- `worker`: Celery worker for background ingestion.
- `postgres`: PostgreSQL + pgvector for metadata and embeddings.
- `redis`: Celery broker/result backend and chat rate-limit counter.

### 2.2 High-level request flow
1. Browser authenticates through `/auth/login`; API sets JWT + CSRF cookies.
2. Frontend calls API with cookie auth (`credentials: include`).
3. API enforces RBAC and CSRF on sensitive mutating requests.
4. If license enforcement is enabled, API guard validates the local workspace license and blocks protected routes when the installation is inactive.
5. For document upload, API stores file metadata and enqueues ingestion task.
6. Worker extracts text, chunks it, computes embeddings, and writes chunk vectors to Postgres.
7. Chat retrieves relevant chunks, streams LLM output, and persists answer + source references.

### 2.3 Ingestion flow (PDF/TXT/CSV)
1. Upload validation in API: extension, MIME type, max file size.
2. Document created with status `uploaded`.
3. Celery task `ingest_document` starts.
4. Worker sets `processing`, clears old chunks, extracts text:
   - PDF: per-page extraction with `page_number` metadata.
   - TXT: full text extraction.
   - CSV: row-based extraction with `csv_row_start` / `csv_row_end`.
5. Chunking with overlap (default `chunk_size=3800`, `overlap=450`).
6. Embeddings generated via current runtime provider.
7. Chunks stored in `chunks` table (pgvector).
8. Document set to `ready` or `failed` with `error_text`.

## 3. Roles, Permissions, and Security Model
### 3.1 Roles
- `admin`: full access across app, user management, taxonomy updates/deletes, settings writes.
- `editor`: can upload/manage own documents, create tags/departments/folders, use dashboard and settings read/test.
- `viewer`: read-limited user; cannot mutate taxonomy/documents/settings, but can use Chat, Email Helper (when enabled), and manage own Personal Notes.
- All authenticated roles can update their own login credentials (email/password) in Settings.
- If the installation license is inactive and license enforcement is enabled, protected app usage is blocked globally; admins can still access Settings for recovery.

### 3.2 Document visibility rules
For non-admin users, visible documents are:
- Company-visible documents.
- Department-visible documents if `user.department_id == document.department_id`.
- Private documents owned by the current user.

### 3.3 Document management permissions
- `admin`: can manage any document.
- `editor`: can manage only owned documents.
- `viewer`: cannot manage documents.

### 3.4 Authentication and CSRF model
- JWT is stored as HTTP-only cookie (`kb_access_token`).
- CSRF token is stored in non-HTTP-only cookie (`kb_csrf_token`) and must be sent as header `X-CSRF-Token` for mutating endpoints.
- Frontend middleware redirects unauthenticated users to `/login`.
- `/auth/login` and `/auth/me` also return license entitlement flags (`license_enabled`, `license_active`, `license_status`, `license_grace_until`) used by frontend guards.
- Backend enforces a global license guard on authenticated protected routes when the installation is inactive.

### 3.5 Chat rate limiting
- Per-user, Redis-backed windowed limit.
- Default window/limit from config:
  - `CHAT_RATE_LIMIT_WINDOW_SEC=300`
  - `CHAT_RATE_LIMIT_MAX_REQUESTS=30`

## 4. UI Feature Reference
### `/` (Home)
- Server-side redirect to `/dashboard`.

### `/login`
- Email/password login form.
- On success, redirects to `/dashboard`.

### `/subscription-inactive`
- Read-only blocking page shown when license enforcement is enabled and the local installation is inactive.
- All non-admin users are redirected here from protected routes.
- The page explains that a 7-day free trial is available for new workspaces.
- Admin users see recovery guidance: click `Open License Settings`, then `Buy / Renew Subscription` to start the 7-day free trial, and return to complete activation or validation if needed.
- Non-admin users are told to contact their workspace administrator, who can start the 7-day free trial from Settings.

### Global header
- Navigation: Dashboard, Documents, AI Document Summarizer, Chat, Personal Notes, Admin, Settings.
- `Email Helper` tab is shown only when globally enabled by admin.
- Logout action via `/auth/logout`.
- If license enforcement is enabled and the local installation is inactive, client-side guard redirects users to `/subscription-inactive` (admin may still open `/settings` for recovery).

### `/dashboard`
- KPI cards: documents, chunks, users, chats, failed ingestions, last ingestion.
- Charts: daily chats, top departments, top tags.
- Knowledge gaps list (latest low-confidence/no-source questions).
- Admin-only: clear knowledge gaps action.
- Dashboard chat/gap metrics are scoped to normal `/chat` sessions (Email Helper is excluded).

### `/documents`
- Upload dialog:
  - File input (PDF/TXT/CSV).
  - Visibility selection (`company`, `department`, `private`).
  - Folder selection.
  - Department selection.
  - Tag multi-select.
  - Inline creation of folders/tags/departments (admin/editor API permissions apply).
- Documents table:
  - Folder filter.
  - Folder column for visibility across all users.
  - Status labels and timestamps.
  - Per-document actions: view original file, index, and delete.
  - `View` opens the original uploaded file in a new browser tab. Inline preview depends on browser support for the file type.
- Auto-refresh while ingestion is in `uploaded` or `processing`.

### `/documents/[id]`
- Document detail metadata:
  - MIME, size, visibility, chunk count, status badges.
  - Ingestion error display when `failed`.
- Actions:
  - Re-index document.
  - Delete document.
  - Edit folder, department, and tags.
  - Inline add folder/tag/department.

### `/ai-document-summarizer`
- Purpose:
  - Upload external documents and summarize the most important information.
  - Chat with AI specifically about one selected external document.
- Isolation:
  - These uploads are not part of internal company knowledge (`documents/chunks`).
  - Retrieval for this page uses only the selected external document context.
- Supported formats:
  - PDF, TXT, CSV, DOCX.
  - Legacy DOC is intentionally rejected (user should upload DOCX).
- Layout:
  - Left panel: upload + document list (status, delete).
  - Right panel: summary action/result + persistent per-document chat.

### `/chat`
- Session management:
  - Create new session.
  - List/reopen sessions.
  - Clear all sessions.
- Chat ask flow:
  - Streams response over SSE.
  - Persists answer and source references.
  - Displays warning for low retrieval confidence.
- Filters:
  - Department filter.
  - Single-tag filter.
- Per-assistant-answer actions:
  - Thumb feedback (`up`/`down`).
  - Print-friendly view.
- Sources side panel:
  - Shows document, chunk metadata, snippet.

### `/personal-notes`
- Purpose:
  - Manage private notes for your own account.
  - Create, edit, and delete notes with a compact split-layout editor.
  - `New Note` creates an instant draft immediately (`Untitled Note`) and opens it.
- Privacy:
  - Notes are owner-only and not visible to other users.
  - Notes are not used in Chat or Email Helper retrieval.
- Layout:
  - Left panel: search + note list (title, preview, updated timestamp).
  - Left panel cards include a color-coded priority badge (`none`, `low`, `medium`, `high`).
  - Right panel: title/content editor, priority selector, save and delete actions.

### `/email-helper`
- Purpose:
  - Paste incoming email text.
  - Generate a ready-to-send reply grounded in indexed company knowledge.
  - Output is plain response email text only (no technical rationale block).
- Access:
  - Available for all authenticated users only when globally enabled by admin.
  - If disabled, page access is blocked and frontend redirects to Dashboard with a short notice.
- Left archive panel:
  - Separate archive from normal `/chat`.
  - Reopen archived email-helper chats.
  - Delete archived chats.
  - Start a new chat.
- Main conversation panel:
  - Streams generated reply text.
  - Shows low-confidence warning when retrieval confidence is limited.
  - Copy assistant replies to clipboard with one click.

### `/admin/users`
- User CRUD (admin-only backend).
- Create users with role assignment.
- Delete users.
- Quick links to taxonomy pages (`/admin/tags`, `/admin/departments`, `/admin/folders`).

### `/admin/tags`
- Tag management table.
- Add, edit, delete tags.
- Deletion requires confirmation and removes links from documents.
- Toast feedback for load/create/update/delete results.

### `/admin/departments`
- Department management table.
- Add, edit, delete departments.
- Deletion confirmation explicitly notes automatic unassignment for users/documents.
- Toast feedback for load/create/update/delete results.

### `/admin/folders`
- Folder management table.
- Add, edit, delete global folders.
- Deletion confirmation explicitly notes automatic unassignment for documents.
- Toast feedback for load/create/update/delete results.

### `/settings`
- Account Security:
  - All authenticated users can update own login email/password.
  - Current password is required.
  - On successful change, auth cookies are cleared and re-login is required.
  - Bootstrap admins are forced into an initial security setup and must change both email and password before using the rest of the app.
- Provider settings overview.
- Runtime provider switch (`openai` or `ollama`).
- Optional OpenAI key update.
- Admin-only OpenAI key delete action (hard delete until a new key is saved).
- Ollama URL/model configuration.
- Admin-only inline setup help in Runtime Provider:
  - OpenAI API key creation guidance with official OpenAI API key link.
  - Ollama integration guidance (local/remote runtime via base URL), including Docker host note (`http://host.docker.internal:11434`) and official Ollama links.
- Connection tests:
  - Test OpenAI endpoints.
  - Test Ollama endpoints.
- Data settings:
  - Retention days.
  - Max upload MB.
  - Global Email Helper toggle (`enabled` / `disabled`).
- License & Subscription (admin-only actions in Runtime Provider area):
  - View local license status, workspace ID, local activation state, stored-license-key state, grace window, last validation timestamp, and license-server URL.
  - Start hosted checkout on the external license server (`Buy / Renew Subscription`) to begin the 7-day free trial or renew the subscription.
  - Open the Polar customer portal in a new tab (`Access My Purchases`) to sign in with the billing email used for purchase/subscription, review purchases, manage the subscription, or cancel it.
  - Paste the real Polar-generated license key from the hosted checkout success page.
  - Activate the current installation after checkout (`Activate This Installation`).
  - Revalidate the currently stored local activation (`Validate Installation`).
  - Remove the local activation while keeping the stored encrypted license key for later recovery (`Deactivate This Installation`).
  - License checkout, key issuance, and Polar synchronization are handled by the external license server at `https://app.automateki.de`.
- Support Diagnostics (admin-only):
  - Export recent API and worker support logs as a bounded ZIP archive.
  - Intended for troubleshooting operational events and errors without exporting secrets or document/chat contents.
- Save permissions:
  - Admin can save provider/data settings.
  - Admin and editor can read settings and run provider tests.

## 5. API Reference
All endpoints are mounted without a global `/api` prefix.

CSRF note: login/logout and provider connectivity tests are intentionally callable without CSRF validation; taxonomy/document/session/data/provider/license admin mutations require it.

### 5.1 Auth
| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/auth/login` | Public | Authenticate user and set JWT + CSRF cookies; includes license entitlement flags and `must_change_credentials` for bootstrap admins. |
| POST | `/auth/logout` | Authenticated cookie context | Clear auth cookies. |
| GET | `/auth/me` | Authenticated | Return current user profile, role, Email Helper flag, license entitlement flags, and `must_change_credentials`. |
| PUT | `/auth/me/credentials` | Authenticated + CSRF | Update own email/password (current password required) and force re-login by clearing auth cookies. |

### 5.2 Users
| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/users` | Admin | List users. |
| POST | `/users` | Admin + CSRF | Create user. |
| PUT | `/users/{user_id}` | Admin + CSRF | Update user fields. |
| DELETE | `/users/{user_id}` | Admin + CSRF | Delete user. |

### 5.3 Tags
| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/tags` | Authenticated | List tags (sorted by name). |
| POST | `/tags` | Admin/Editor + CSRF | Create tag. |
| PUT | `/tags/{tag_id}` | Admin + CSRF | Rename tag. |
| DELETE | `/tags/{tag_id}` | Admin + CSRF | Delete tag (document tag links are cascade-removed). |

### 5.4 Departments
| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/departments` | Authenticated | List departments (sorted by name). |
| POST | `/departments` | Admin/Editor + CSRF | Create department. |
| PUT | `/departments/{department_id}` | Admin + CSRF | Rename department. |
| DELETE | `/departments/{department_id}` | Admin + CSRF | Delete department; users/documents are auto-unassigned (`department_id = null`). |

### 5.5 Folders
| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/folders` | Authenticated | List global folders (sorted by name). |
| POST | `/folders` | Admin/Editor + CSRF | Create folder. |
| PUT | `/folders/{folder_id}` | Admin/Editor + CSRF | Rename folder. |
| DELETE | `/folders/{folder_id}` | Admin/Editor + CSRF | Delete folder; documents are auto-unassigned (`folder_id = null`). |

### 5.6 Documents
| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/documents/upload` | Admin/Editor + CSRF | Upload file (optional `folder_id`) and enqueue ingestion. |
| GET | `/documents` | Authenticated (RBAC filtered) | List accessible documents. |
| GET | `/documents/{document_id}` | Authenticated + document access check | Return detailed document metadata and tag IDs. |
| GET | `/documents/{document_id}/file` | Authenticated + document access check | Open the original uploaded file with inline browser preview when supported. |
| PUT | `/documents/{document_id}/metadata` | Admin/Editor + CSRF + manage check | Update folder/department/tag assignments. |
| DELETE | `/documents/{document_id}` | Admin/Editor + CSRF + manage check | Delete document and stored file. |
| POST | `/documents/{document_id}/index` | Admin/Editor + CSRF + manage check | Requeue indexing. |
| POST | `/documents/{document_id}/reingest` | Admin/Editor + CSRF + manage check | Alias to index endpoint. |

### 5.7 Chat
| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/chat/sessions` | Authenticated + CSRF | Create normal chat session. |
| GET | `/chat/sessions` | Authenticated | List own normal chat sessions. |
| DELETE | `/chat/sessions` | Authenticated + CSRF | Delete all own normal chat sessions. |
| GET | `/chat/sessions/{session_id}` | Authenticated (owner only) | Get messages with persisted sources. |
| POST | `/chat/ask` | Authenticated | Ask question; SSE stream with `token`, `sources`, `done`, `error`. |
| POST | `/chat/feedback` | Authenticated + CSRF (owner scope) | Store thumbs feedback for assistant message. |

### 5.8 Personal Notes
| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/personal-notes` | Authenticated | List own notes (sorted by `updated_at desc`). |
| POST | `/personal-notes` | Authenticated + CSRF | Create own note (`title`, `content`, optional `priority`). |
| PUT | `/personal-notes/{note_id}` | Authenticated + CSRF (owner only) | Update own note fields (`title`, `content`, `priority`). |
| DELETE | `/personal-notes/{note_id}` | Authenticated + CSRF (owner only) | Delete own note. |

### 5.9 Email Helper
All endpoints in this group enforce the global feature flag and return `403` when Email Helper is disabled.

| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/email-helper/sessions` | Authenticated + CSRF + feature enabled | Create email-helper session. |
| GET | `/email-helper/sessions` | Authenticated + feature enabled | List own email-helper archived sessions. |
| GET | `/email-helper/sessions/{session_id}` | Authenticated + feature enabled (owner only) | Load one archived email-helper chat. |
| DELETE | `/email-helper/sessions/{session_id}` | Authenticated + CSRF + feature enabled (owner only) | Delete one archived email-helper chat. |
| POST | `/email-helper/ask` | Authenticated + feature enabled | Generate streamed ready-to-send email reply (`token`, `done`, `error`). |

### 5.10 AI Document Summarizer
| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/ai-document-summarizer/documents/upload` | Authenticated + CSRF | Upload external document and enqueue isolated indexing. |
| GET | `/ai-document-summarizer/documents` | Authenticated | List own external summarizer documents. |
| GET | `/ai-document-summarizer/documents/{document_id}` | Authenticated (owner only) | Get one external document with chunk/message counts. |
| DELETE | `/ai-document-summarizer/documents/{document_id}` | Authenticated + CSRF (owner only) | Delete external document, related chunks/messages, and stored file. |
| POST | `/ai-document-summarizer/documents/{document_id}/summarize` | Authenticated + CSRF (owner only) | Generate and persist summary text for selected external document. |
| GET | `/ai-document-summarizer/documents/{document_id}/messages` | Authenticated (owner only) | Get persistent chat history for selected external document. |
| POST | `/ai-document-summarizer/documents/{document_id}/ask` | Authenticated (owner only) | Ask questions about selected external document (`token`, `sources`, `done`, `error`). |

### 5.11 Dashboard
| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/dashboard/kpis` | Admin/Editor | KPI metrics. |
| GET | `/dashboard/charts` | Admin/Editor | Chart datasets (daily chats, top tags/departments, unanswered trend). |
| GET | `/dashboard/gaps` | Admin/Editor | Recent low-confidence/no-source retrieval logs. |
| DELETE | `/dashboard/gaps` | Admin + CSRF | Clear gap logs. |

### 5.12 Settings
| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/settings/data` | Admin/Editor | Get retention/upload limits and global Email Helper toggle. |
| PUT | `/settings/data` | Admin + CSRF | Update retention/upload limits and global Email Helper toggle. |
| GET | `/settings/providers` | Admin/Editor | Get runtime provider settings. |
| PUT | `/settings/providers` | Admin + CSRF | Update runtime provider + model/key/base URL settings. |
| DELETE | `/settings/providers/openai-key` | Admin + CSRF | Hard-delete runtime OpenAI key (disables OpenAI key usage until a new key is saved). |
| POST | `/settings/providers/test-openai` | Admin/Editor | Test OpenAI chat + embeddings endpoints. |
| POST | `/settings/providers/test-ollama` | Admin/Editor | Test Ollama chat + embeddings endpoints. |
| GET | `/settings/network-helper` | Admin | Get the saved LAN host override used by the Network Access Helper. |
| PUT | `/settings/network-helper` | Admin + CSRF | Save or clear the LAN host override used to generate LAN/WLAN share URLs and `.env` values. |
| GET | `/settings/log-export` | Admin | Download a bounded ZIP export of recent API + worker support logs. |

### 5.13 License
| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/license/status` | Authenticated | Get current local license state for the workspace installation, including the effective billing email and its source. |
| PUT | `/license/billing-email` | Admin + CSRF | Save or clear the runtime billing email used for Polar checkout and activation. |
| POST | `/license/checkout` | Admin + CSRF | Request hosted checkout URL from the external license server. |
| POST | `/license/activate` | Admin + CSRF | Activate the current installation with a pasted Polar-generated `license_key`; the local app stores that key encrypted for later validation and recovery. |
| POST | `/license/validate` | Admin + CSRF | Revalidate the stored local activation with the external license server using the locally stored encrypted license key. |
| POST | `/license/deactivate` | Admin + CSRF | Deactivate the current local installation while keeping the stored encrypted license key for fast reactivation. |

### 5.14 Health
| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/health` | Public | Service health summary (db, redis, runtime provider status). |

## 6. Configuration and Environment Variables
Configuration is loaded from `.env` (see `.env.example`).

### 6.1 Core app/runtime
- `DATABASE_URL`: SQLAlchemy database URL.
- `REDIS_URL`: Redis URL for Celery and rate limiting.
- `FRONTEND_URL`: Allowed CORS origin.
- `NEXT_PUBLIC_API_URL`: Frontend API base URL.

### 6.2 Auth/security
- `JWT_SECRET`: signing key for access tokens.
- `SECRETS_ENCRYPTION_KEY`: optional dedicated encryption seed for stored secrets.
- `JWT_ALGORITHM`: token algorithm (default `HS256`).
- `JWT_EXPIRE_HOURS`: cookie/token lifetime.
- `COOKIE_SECURE`: secure cookie flag.

### 6.3 Providers
- `LLM_PROVIDER`: startup default (`openai` or `ollama`).
- `EMBEDDINGS_PROVIDER`: startup default (`openai` or `ollama`).
- `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL`, `OPENAI_EMBEDDINGS_MODEL`.
- `OLLAMA_BASE_URL`, `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBEDDINGS_MODEL`.

### 6.4 Document storage and logging controls
- `FILE_STORAGE_PATH`: upload storage path (`/data/uploads` in Docker).
- `APP_LOG_DIR`: application support log path (`/data/logs` in Docker).
- `APP_LOG_LEVEL`: log verbosity for app-level diagnostic events.
- `APP_LOG_MAX_BYTES`: per-service log rotation size limit.
- `APP_LOG_BACKUP_COUNT`: number of rotated log files to keep per service.
- `APP_LOG_EXPORT_WINDOW_HOURS`: maximum age of log entries included in admin exports.
- `APP_LOG_EXPORT_MAX_LINES`: maximum number of recent log lines included per service in an export.
- `MAX_UPLOAD_MB`: upload limit.
- `allowed_extensions`: defaults to `pdf,txt,csv` (config code).
- `allowed_mime_types`: supported MIME list (config code).
- AI Document Summarizer supports external uploads with `pdf,txt,csv,docx` in its dedicated route flow.

### 6.5 Retrieval and rate-limit controls
- `embedding_dimension` (default `1536`).
- `retrieval_top_k` (default `8`).
- `retrieval_low_conf_threshold` (default `0.35`).
- `chat_rate_limit_window_sec` (default `300`).
- `chat_rate_limit_max_requests` (default `30`).

### 6.6 Runtime provider behavior
- Provider settings are persisted in `app_settings`.
- OpenAI key is encrypted at rest.
- Admin hard-delete of OpenAI key is persisted in `app_settings` and takes precedence over `.env` fallback.
- Runtime selection applies to new requests immediately.
- This deployment enforces matched provider pair (`llm_provider == embeddings_provider`).
- Global Email Helper availability is persisted in `app_settings` (`email_helper_enabled`).

### 6.7 License-server variables
- `LICENSE_SERVER_BASE_URL`: base URL of the external license server (`https://app.automateki.de`).
- `LICENSE_SERVER_ADMIN_TOKEN`: static Bearer JWT used only by the trusted local backend for `/billing/*` calls.
- `LICENSE_WORKSPACE_ID`: stable workspace identifier used for checkout, sync, activation, and validation.
- `LICENSE_COMPANY_NAME`: company/workspace name sent to the external license server.
- `LICENSE_BILLING_EMAIL`: optional operator fallback for checkout/activation when no runtime billing email has been saved in Settings.
- `LICENSE_ENFORCEMENT_ENABLED`: enable/disable hard blocking when the local installation license is inactive.
- `LICENSE_VALIDATE_INTERVAL_HOURS`: how often the app should revalidate the cached activation with the external server.
- `LICENSE_OFFLINE_GRACE_HOURS`: offline grace period after a successful validation if the license server is temporarily unreachable. Explicit inactive/invalid responses do not receive grace.

Local runtime license state is persisted in `app_settings` (workspace ID, machine fingerprint, runtime billing email, encrypted Polar license key, local instance ID, status, current period end, last validation/check timestamps, grace deadline, and last error).

## 7. Operations and Runtime Management
### 7.1 Start stack
```bash
cp .env.example .env
docker compose up --build
```

### 7.2 URLs
- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`

### 7.3 LAN Deployment (Company Network)
- `Settings > Network Access Helper` is the easiest in-app way to generate the right LAN/WLAN URLs, `.env` snippet, and rebuild command for the current installation.
- With the current Docker port publishing, the app is reachable from LAN peers through the host machine IP/DNS:
  - Frontend: `http://<HOST_IP>:3000`
  - API: `http://<HOST_IP>:8000`
- For reliable LAN-wide frontend usage, do **not** keep `localhost` in runtime-facing `.env` values.
- Required `.env` setup for LAN clients:
  - `NEXT_PUBLIC_API_URL` must be set to host IP or internal DNS (not `localhost`).
  - `FRONTEND_URL` must match the same host IP/DNS origin for backend CORS.
- Example:
```env
NEXT_PUBLIC_API_URL=http://192.168.x.x:8000
FRONTEND_URL=http://192.168.x.x:3000
```
- Keep one consistent origin style for all users (IP/DNS), and avoid mixed usage with `localhost`.
- After changing these values, rebuild/restart frontend and API:
```bash
docker compose up -d --build api frontend
```
- Reason: `NEXT_PUBLIC_API_URL` is embedded into the frontend build output.
- The Network Access Helper shows this same command after it generates the LAN values.
- Network prerequisites:
  - Host firewall must allow inbound LAN connections.
  - Internal routing/ACL/VLAN policies must permit access to the host.
- Security note for LAN/production hardening:
  - Restrict infrastructure ports `5432` (Postgres) and `6379` (Redis) unless explicitly required.

### 7.4 Migrations
- Applied automatically when API starts:
  - `alembic upgrade head`
- Manual run:
```bash
docker compose exec api alembic upgrade head
```

### 7.5 Bootstrap first admin
- On a fresh installation, the API creates one bootstrap admin automatically if no admin exists yet.
- Bootstrap email: `admin@local`
- Bootstrap password: strong random password generated once per installation
- Delivery method: printed once to the API startup console output

To retrieve the credentials:
```bash
docker compose logs api
```

Behavior:
- The bootstrap admin is marked for initial security setup.
- On first login, the user is forced to `Settings`.
- The bootstrap admin must change both email and password before using the rest of the app.

Emergency/manual fallback:
```bash
docker compose exec api python -m app.scripts.seed_admin --email admin@example.com --password ChangeMe123!
```

### 7.6 Useful runtime checks
- Service states:
```bash
docker compose ps
```
- API health:
```bash
curl -sS http://localhost:8000/health
```
- Worker ingestion task visibility:
```bash
docker compose logs worker | grep ingest_document
```
- Run backend tests:
```bash
docker compose exec api pytest -q
```

### 7.7 External license-server setup
1. Configure local app env variables in `.env` and rebuild API/frontend:
```bash
docker compose up -d --build api frontend
```
2. Set:
   - `LICENSE_SERVER_BASE_URL=https://app.automateki.de`
   - `LICENSE_SERVER_ADMIN_TOKEN=<static-admin-bearer-jwt>`
   - `LICENSE_WORKSPACE_ID=<stable-workspace-id>`
   - `LICENSE_ENFORCEMENT_ENABLED=true` as the standard production default for current and fresh installations
3. In app Settings (admin), use:
   - `Buy / Renew Subscription` to open hosted checkout on `app.automateki.de` and start the 7-day free trial
   - copy the Polar-generated license key from the hosted success page
   - paste that key into `License & Subscription`
   - `Activate This Installation` after checkout completes
   - `Validate Installation` for a manual refresh if needed
   - copy or save the shown `Workspace ID`; that exact value is required if the same licensed installation is restored after a reinstall
4. On fresh installs, normal protected app usage remains blocked until an admin completes checkout, starts the 7-day free trial or paid subscription, pastes the Polar license key, and activates the installation.
5. The local app does not talk to Polar directly anymore. Polar credentials, webhook processing, and subscription synchronization live only on the external license server.
6. The production Polar access token used by the external license server must support both `license_keys:read` and `license_keys:write`; otherwise the hosted checkout success page may not be able to display the generated key and activation can fail.
7. Device activation limits are enforced by the external license server, not by Polar. The current production default is `3` active installations per workspace.
8. If an admin reaches the device limit or loses the local activation ID after a reinstall, `Settings > License & Subscription` now shows activation usage and provides `Reset All Activations` as the v1 recovery path.
9. The Quick Start installer now writes a non-empty `LICENSE_WORKSPACE_ID` into `.env` and prints it at the end of installation so admins can keep it for manual restore.
10. Under the current strict-restore policy, a billing email that is already linked to an older Polar workspace should be reused only by restoring that original `LICENSE_WORKSPACE_ID`. Use a different billing email if you want to purchase a truly new workspace.

### 7.8 Document lifecycle
- `uploaded`: queued.
- `processing`: ingestion running.
- `ready`: indexed and searchable.
- `failed`: ingestion error captured in `error_text`.

## 8. Troubleshooting Guide
### Documents stay in `uploaded`
- Verify worker is running (`docker compose ps`).
- Check worker logs for ingestion task registration/errors.
- Confirm Redis health (worker queue dependency).

### Document ends in `failed`
- Open document detail page and inspect `error_text`.
- Common causes: empty extractable text, unsupported/invalid file content.

### Chat quality is low or warns about confidence
- Ensure relevant documents are in `ready` state.
- Refine question specificity.
- Use department/tag filters in chat.
- Re-index stale documents when needed.

### Provider test or generation failures
- Open Settings and run provider tests.
- Verify OpenAI key and model availability.
- Verify Ollama base URL/model names and reachability from Docker network.

### Permission/403 issues
- Confirm role-based restrictions for endpoint/action.
- For mutating actions, ensure CSRF header is sent alongside cookie token.

### License inactive / enforcement block
- Confirm `LICENSE_ENFORCEMENT_ENABLED=true` only when the external license server is configured.
- Check `/license/status` for `last_error`, `license_status`, and `grace_until`.
- Verify `LICENSE_SERVER_BASE_URL` and `LICENSE_SERVER_ADMIN_TOKEN`.
- If the license server is temporarily unreachable, the app continues during the configured grace window and then blocks after grace expiry.
- If the license server explicitly reports an inactive or invalid installation, the app does not apply grace and blocks immediately until admin recovery succeeds.
- If activation is missing, use `Buy / Renew Subscription` on `app.automateki.de`, copy the Polar-generated license key from the hosted success page, paste it into Settings, then use `Activate This Installation`.
- In Settings, license actions show an inline success/error banner directly inside `License & Subscription` so activation and validation results are visible immediately.
- If the workspace has already consumed all activation slots, use `Reset All Activations` in Settings, then retry `Activate This Installation`.
- If activation fails with `License key does not match this workspace.`, the stored Polar key belongs to a different `LICENSE_WORKSPACE_ID`. Restore the original Workspace ID in `.env`, rebuild the API, and retry activation. Otherwise start a new checkout for the new workspace.
- If checkout is blocked because the billing email is already linked to another Workspace ID on Polar, restore the original `LICENSE_WORKSPACE_ID` for that purchase or save a different billing email before retrying checkout for a brand new workspace.
- If checkout is blocked because the billing email is invalid, save a real reachable `Billing Email` directly in `Settings > License & Subscription` and retry `Buy / Renew Subscription`. Use `LICENSE_BILLING_EMAIL` in `.env` only as an operator fallback.

## 9. Security Notes
- JWT is cookie-based with configurable secure flag.
- CSRF uses double-submit cookie/header validation on mutating routes.
- Server-side RBAC enforcement is applied per endpoint and per-document checks.
- OpenAI API key is stored encrypted in settings storage.
- Chat endpoint enforces per-user rate limiting.
- AI Document Summarizer data is owner-private and isolated from internal company knowledge retrieval paths.
- Polar webhooks are processed only on the external license server and are signature-validated there.
- License enforcement blocks protected authenticated routes globally when the local installation is inactive (admin Settings + `/license/*` remain recovery paths).

## 10. Current Limits
- No SSO integration.
- No OCR pipeline.
- No legacy DOC parsing support (`.doc` is rejected; upload `.docx` in AI Document Summarizer).
- Single-tenant runtime provider setting (global for the app).
- No multi-tenant isolation model.
- Licensing v1 supports one global monthly plan for the full deployment, backed by the external license server at `https://app.automateki.de`.
