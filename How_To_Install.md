# How To Install KnowledgeBase AI (Docker Desktop)

Comprehensive installation and deployment guide for running KnowledgeBase AI on a local machine and, if required, across a local company network.

## Table of Contents
- [1. What This Guide Covers](#1-what-this-guide-covers)
- [2. Deployment Scenarios](#2-deployment-scenarios)
- [3. System Requirements](#3-system-requirements)
- [4. Package Contents](#4-package-contents)
- [5. Pre-Installation Checklist](#5-pre-installation-checklist)
- [6. Fresh Installation (New Environment)](#6-fresh-installation-new-environment)
- [7. Environment Configuration (`.env`)](#7-environment-configuration-env)
- [8. Start, Verify, and First Login](#8-start-verify-and-first-login)
- [9. LAN / Company Network Access](#9-lan--company-network-access)
- [10. Install With Existing Data (Migration / Handover)](#10-install-with-existing-data-migration--handover)
- [11. Backup and Restore Procedures](#11-backup-and-restore-procedures)
- [12. Updating to a New App Version](#12-updating-to-a-new-app-version)
- [13. Security Recommendations](#13-security-recommendations)
- [14. Troubleshooting](#14-troubleshooting)
- [15. Common Commands](#15-common-commands)
- [16. External License Server Setup](#16-external-license-server-setup)

## 1. What This Guide Covers
This guide explains how to:
- Install and run KnowledgeBase AI on a new computer using Docker Desktop.
- Configure the app for single-user localhost use or LAN-wide access.
- Transfer an existing installation (including data) to another machine.
- Operate, update, and troubleshoot the deployment safely.

## 2. Deployment Scenarios
Use the scenario that matches your goal:

1. **Fresh install (no old data)**
- Best for first-time setup or clean test environments.

2. **Handover install (with existing data)**
- Use when moving the app to another user/computer and keeping users/documents/chats/settings.

3. **LAN-shared host install**
- One host machine runs the stack; multiple users access the frontend from the same network.

## 3. System Requirements
Minimum practical requirements:
- Docker Desktop installed and running.
- 4 CPU cores recommended.
- 8 GB RAM minimum (16 GB recommended for larger documents and better responsiveness).
- At least 10 GB free disk space (more if storing many uploads and embeddings).

Supported host OS:
- macOS, Windows, Linux (with Docker Engine/Docker Desktop compatibility).

Network requirements:
- Internet access is required if using OpenAI.
- Internal network access is required if users connect over LAN.

## 4. Package Contents
A valid handover package should include at least:
- `backend/`
- `frontend/`
- `docker-compose.yml`
- `.env.example`
- `README.md`
- `APP_DOKUMENTATION.md`
- `How_To_Install.md` (this file)

Optional (for data migration):
- SQL dump (e.g. `knowledgebase.sql`)
- Upload archive (e.g. `uploads_data.tgz`)

## 5. Pre-Installation Checklist
Before starting:
- Confirm Docker Desktop is running.
- Ensure ports are free on target machine:
  - `3000` (frontend)
  - `8000` (API)
  - `5432` (Postgres)
  - `6379` (Redis)
- If migrating data, confirm you received:
  - database dump file
  - uploads archive
- Decide whether deployment is:
  - localhost only, or
  - LAN-wide.

## 6. Fresh Installation (New Environment)
Run these steps from the project root (folder containing `docker-compose.yml`).

### Quick Start (One-Line Installer)
For the fastest new-customer install, provide one of these commands on the marketing website:

macOS/Linux:
```bash
curl -fsSL https://knowledgebaseai.de/knowledgebase-ai/install.sh | bash
```

Windows PowerShell:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://knowledgebaseai.de/knowledgebase-ai/install.ps1 | iex"
```

The hosted quick-start installer:
- requires Docker Desktop or Docker Engine to already be installed and running
- downloads the latest stable GitHub release, not the current `main` branch
- creates `.env` automatically with secure local defaults
- starts the Docker stack with `docker compose up -d --build`
- prints the bootstrap admin credentials from the API logs when available

Quick-start defaults:
- `JWT_SECRET` and `SECRETS_ENCRYPTION_KEY` are generated automatically
- `NEXT_PUBLIC_API_URL=http://localhost:8000`
- `FRONTEND_URL=http://localhost:3000`
- `LICENSE_SERVER_BASE_URL=https://app.automateki.de`
- `LICENSE_ENFORCEMENT_ENABLED=true`
- `OPENAI_API_KEY=` remains empty until the admin adds it later in Settings

Important:
- The quick-start flow is for fresh installations only and aborts if `./knowledgebase-ai` already exists.
- The hosted installer also embeds the shared `LICENSE_SERVER_ADMIN_TOKEN` so checkout works immediately after install.
- That makes installation friction lower, but it also means the `/billing/*` protection is no longer based on a secret known only to trusted operators.

### Step 1: Prepare environment file
macOS/Linux:
```bash
cp .env.example .env
```

Windows PowerShell:
```powershell
Copy-Item .env.example .env
```

### Step 2: Edit `.env`
Set at least:
- `JWT_SECRET` to a strong random value.
- `OPENAI_API_KEY` (if OpenAI should be used immediately), or leave empty and set via Settings later.

For localhost-only install, keep:
- `NEXT_PUBLIC_API_URL=http://localhost:8000`
- `FRONTEND_URL=http://localhost:3000`
- `LICENSE_ENFORCEMENT_ENABLED=true` so the installation requires license purchase and activation from the first real use

### Step 3: Build and start services
```bash
docker compose up -d --build
```

This starts:
- `postgres`
- `redis`
- `api`
- `worker`
- `frontend`

### Step 4: Retrieve bootstrap admin credentials
```bash
docker compose logs api
```
On a fresh installation, the API creates a one-time bootstrap admin automatically:
- Email: `admin@local`
- Password: randomly generated per installation
- Output location: API container logs only

Sign in with these bootstrap credentials, then immediately complete the forced credential change in `Settings`.

Emergency fallback only:
```bash
docker compose exec api python -m app.scripts.seed_admin --email admin@example.com --password ChangeMe123!
```

## 7. Environment Configuration (`.env`)
Important variables:

- `OPENAI_API_KEY`
  - OpenAI key (can also be set/changed/deleted in Settings by admin).

- `LLM_PROVIDER`, `EMBEDDINGS_PROVIDER`
  - Startup provider defaults (`openai` or `ollama`).

- `DATABASE_URL`, `REDIS_URL`
  - Internal service connectivity.

- `APP_LOG_DIR`, `APP_LOG_LEVEL`, `APP_LOG_MAX_BYTES`, `APP_LOG_BACKUP_COUNT`
  - Admin support-log storage and rotation for recent API/worker diagnostics.

- `APP_LOG_EXPORT_WINDOW_HOURS`, `APP_LOG_EXPORT_MAX_LINES`
  - Limits for the admin-only support log export ZIP.

- `JWT_SECRET`
  - Required for auth token signing; must be strong in real environments.

- `NEXT_PUBLIC_API_URL`
  - Frontend API target URL.
  - **Important:** this value is embedded during frontend build.

- `FRONTEND_URL`
  - Allowed frontend origin for backend CORS.

- `LICENSE_SERVER_BASE_URL`
  - Base URL of the external license server. Use `https://app.automateki.de` in production.

- `LICENSE_SERVER_ADMIN_TOKEN`
  - Static Bearer JWT used only by the trusted local backend when calling admin-protected license-server endpoints.

- `LICENSE_WORKSPACE_ID`
  - Stable external workspace ID used for billing reconciliation and activation validation.

- `LICENSE_COMPANY_NAME`
  - Company or workspace name sent during activation and checkout.

- `LICENSE_BILLING_EMAIL`
  - Reachable billing email sent to the license server for checkout and activation.

- `LICENSE_ENFORCEMENT_ENABLED`
  - Enables or disables hard license enforcement globally.

- `LICENSE_VALIDATE_INTERVAL_HOURS`
  - How often the local app should revalidate the stored activation.

- `LICENSE_OFFLINE_GRACE_HOURS`
  - How long the app may continue after the last successful validation if `app.automateki.de` is temporarily unreachable.

### Provider notes
- OpenAI and Ollama can be switched at runtime in **Settings**.
- Admin can hard-delete the runtime OpenAI key from Settings and later set a new one.

## 8. Start, Verify, and First Login

### Check container health
```bash
docker compose ps
```

Expected: all services `Up` (postgres/redis typically `healthy`).

### API health endpoint
```bash
curl -sS http://localhost:8000/health
```

Expected: JSON response with status and provider/db/redis fields.

### Open the app
- Frontend: `http://localhost:3000`
- Login with the bootstrap admin credentials from `docker compose logs api`.
- The bootstrap admin is forced to `Settings` on first login and must change both email and password before using the rest of the app.
- Any authenticated user can later update own email/password in `Settings > Account Security`.

## 9. LAN / Company Network Access
If one host machine should serve users in the local network:

### 9.1 LAN URLs
With current compose ports, app is reachable via host IP:
- Frontend: `http://<HOST_IP>:3000`
- API: `http://<HOST_IP>:8000`

### 9.2 Required `.env` values for LAN
Do not use `localhost` for LAN clients.

Use host IP or internal DNS:
```env
NEXT_PUBLIC_API_URL=http://192.168.x.x:8000
FRONTEND_URL=http://192.168.x.x:3000
```

Rules:
- `NEXT_PUBLIC_API_URL` must point to API as seen by client browsers.
- `FRONTEND_URL` must match the exact frontend origin used by clients.
- Avoid mixing origins (`localhost` for some users, IP/DNS for others).

### 9.3 Rebuild after LAN config change
Required command:
```bash
docker compose up -d --build frontend api
```

Reason:
- `NEXT_PUBLIC_API_URL` is compiled into the frontend build output.

### 9.4 Network prerequisites
- Host firewall must allow inbound connections on required ports.
- LAN routing/VLAN/ACL policies must allow client-to-host traffic.

## 10. Install With Existing Data (Migration / Handover)
Use this when transferring to a new computer and preserving existing data.

### 10.1 What must be transferred
Required for full continuity:
- App source package (project files)
- Database dump (`knowledgebase.sql` or equivalent)
- Upload archive (`uploads_data.tgz` or equivalent)

### 10.2 Prepare new machine
1. Unpack project ZIP.
2. Create/edit `.env`.
3. Start stack once:
```bash
docker compose up -d --build
```

### 10.3 Restore database
```bash
cat backup/knowledgebase.sql | docker compose exec -T postgres psql -U postgres -d knowledgebase
```

### 10.4 Restore uploads
```bash
cat backup/uploads_data.tgz | docker compose exec -T api sh -c "mkdir -p /data/uploads && tar -xzf - -C /data/uploads"
```

### 10.5 Restart services
```bash
docker compose restart api worker frontend
```

## 11. Backup and Restore Procedures

### 11.1 Create backup on source machine
```bash
mkdir -p backup
docker compose exec -T postgres pg_dump -U postgres -d knowledgebase > backup/knowledgebase.sql
docker compose exec -T api sh -c "tar -czf - -C /data/uploads ." > backup/uploads_data.tgz
```

### 11.2 Files to share for migration
- `backup/knowledgebase.sql`
- `backup/uploads_data.tgz`
- Project ZIP (without secret `.env` preferred)

### 11.3 Secret handling recommendation
- Prefer not to share real `.env` with API keys and secrets.
- On target machine, set fresh secrets (`JWT_SECRET`, provider keys).
- Rotate keys after handover when possible.

## 12. Updating to a New App Version
Typical update flow:

1. Backup DB + uploads first.
2. Replace/merge project files with new version.
3. Review `.env` for new variables if needed.
4. Rebuild and start:
```bash
docker compose up -d --build
```
5. Verify:
```bash
docker compose ps
curl -sS http://localhost:8000/health
```

Alembic migrations run automatically when `api` starts.

## 13. Security Recommendations
- Always set a strong `JWT_SECRET`.
- Keep API keys out of shared archives unless absolutely necessary.
- Restrict publicly exposed infra ports in hardened environments:
  - `5432` (Postgres)
  - `6379` (Redis)
- Use firewall rules to limit access to trusted hosts/subnets.
- Use HTTPS/reverse proxy for non-localhost production-like deployments.

## 14. Troubleshooting

### Containers do not start
```bash
docker compose ps
docker compose logs api
docker compose logs frontend
docker compose logs worker
```

### Frontend opens but login/API fails on LAN
Likely cause:
- `NEXT_PUBLIC_API_URL` still points to `localhost`.

Fix:
1. Set `.env` LAN values for `NEXT_PUBLIC_API_URL` and `FRONTEND_URL`.
2. Rebuild:
```bash
docker compose up -d --build frontend api
```

### Port already in use
Symptoms:
- Docker errors about port bind failures.

Fix options:
- Stop conflicting local services.
- Or change published ports in `docker-compose.yml` and align URLs accordingly.

### OpenAI key appears not configured
Possible causes:
- Key not set.
- Runtime key was hard-deleted in Settings.

Fix:
- Enter new OpenAI key in Settings and save provider settings.

### Upload/chat behavior inconsistent after migration
Likely cause:
- DB restored but uploads not restored (or vice versa).

Fix:
- Ensure both DB dump and uploads archive are restored.

### App redirects to `/subscription-inactive`
Likely causes:
- License enforcement is enabled but no active local license is stored.
- The external license server cannot be reached and the grace window already expired.

Fix:
1. Check admin `Settings > Runtime Provider > License & Subscription` status and last error.
2. Verify `LICENSE_SERVER_BASE_URL` and `LICENSE_SERVER_ADMIN_TOKEN`.
3. Click `Validate Installation` as admin.
4. If no activation is stored yet, click `Buy / Renew Subscription` on `app.automateki.de`, then click `Activate This Installation`.
5. If you need a support bundle, open `Settings > Support Diagnostics` and click `Export Support Logs`.

## 15. Common Commands

Start stack:
```bash
docker compose up -d --build
```

Stop stack:
```bash
docker compose down
```

Restart selected services:
```bash
docker compose restart api worker frontend
```

Check service status:
```bash
docker compose ps
```

Run backend tests:
```bash
docker compose exec api pytest -q
```

API health check:
```bash
curl -sS http://localhost:8000/health
```

## 16. External License Server Setup
This section configures app monetization through the hosted license server at `https://app.automateki.de`.

### 16.1 Prepare `.env` values
Set these values in `.env`:
```env
LICENSE_SERVER_BASE_URL=https://app.automateki.de
LICENSE_SERVER_ADMIN_TOKEN=<static_admin_bearer_jwt>
LICENSE_WORKSPACE_ID=<stable_workspace_id>
LICENSE_COMPANY_NAME=KnowledgeBase AI
LICENSE_BILLING_EMAIL=billing@example.com
LICENSE_ENFORCEMENT_ENABLED=true
LICENSE_VALIDATE_INTERVAL_HOURS=6
LICENSE_OFFLINE_GRACE_HOURS=24
```

Notes:
- `LICENSE_ENFORCEMENT_ENABLED=true` is now the default and recommended production setting for both current and fresh installations.
- `LICENSE_SERVER_ADMIN_TOKEN` belongs only in the trusted local backend and is unrelated to Polar.
- The local app no longer stores Polar credentials or receives Polar webhooks directly.
- The local app stores the pasted Polar license key encrypted after activation and reuses it for later validation and recovery.
- `LICENSE_WORKSPACE_ID` is the restore anchor for the licensed workspace. The one-line installer now generates and stores one automatically in `.env`.
- `LICENSE_BILLING_EMAIL` is now only an optional operator fallback. Admins can save or change the real billing email directly in `Settings > License & Subscription`.
- On a fresh install, normal protected app usage stays blocked until an admin completes checkout, pastes the Polar license key, and activates the installation.

### 16.2 Rebuild services after env changes
```bash
docker compose up -d --build api frontend
```

### 16.3 Admin UI flow
1. Login as admin.
2. Open `Settings > Runtime Provider`.
3. In the `License & Subscription` card:
   - Save a real reachable `Billing Email` there if the current admin login email is only a demo/test address.
   - Click `Buy / Renew Subscription` to open hosted checkout on `https://app.automateki.de`.
   - Complete checkout there.
   - Copy the Polar-generated license key from the hosted success page.
   - Return to the local app Settings page and paste the key into `License & Subscription`.
   - Click `Activate This Installation`.
   - Use `Validate Installation` later whenever you want a manual status refresh.
   - Copy or note the displayed `Workspace ID` as well. If the machine is reinstalled later and you want to reuse the same Polar purchase, restore that exact value in `.env` as `LICENSE_WORKSPACE_ID` before restarting the API.
3. For troubleshooting operational issues, open `Settings > Support Diagnostics` and use `Export Support Logs` to download a bounded ZIP of recent API and worker events/errors.

### 16.3 Reinstall / Manual Restore
If the customer reinstalls the app and wants to reuse the same purchased Polar license:
1. Restore the original `LICENSE_WORKSPACE_ID` in `.env`.
2. Restart the API with:
   ```bash
   docker compose up -d --build api
   ```
3. Open `Settings > License & Subscription`.
4. Paste the existing Polar license key and click `Activate This Installation`.

Important:
- Reinstalling with a different `LICENSE_WORKSPACE_ID` intentionally creates a new workspace identity.
- In that case, an old Polar key will fail with `License key does not match this workspace.`
- The correct recovery is either restoring the old Workspace ID or starting a new checkout for the new workspace.
- If checkout is blocked because the billing email is invalid, save a real reachable `Billing Email` directly in `Settings > License & Subscription` and retry. Use `LICENSE_BILLING_EMAIL` in `.env` only as an operator fallback.

### 16.4 Enforcement behavior
- When license enforcement is enabled and the local activation is inactive, protected app routes are blocked.
- Users are redirected to `/subscription-inactive`.
- Admin can still access Settings license controls for recovery.
- The 24-hour grace window applies only to temporary license-server outages. Explicit inactive or invalid-license responses block immediately.

---

If you maintain this app for multiple teams, keep a standardized installation bundle:
- project ZIP (without live secrets),
- this installation guide,
- a short environment profile template (localhost vs LAN),
- and an optional migration backup package (DB + uploads).
