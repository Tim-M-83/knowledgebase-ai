# Handoff: Polar License Server Status and Next Steps

## Summary

Use this as the current source of truth for the Polar license server project.

- Repo: [git@github.com:Tim-M-83/kbai-license-server.git](git@github.com:Tim-M-83/kbai-license-server.git)
- Branch: `main`
- Latest known commit: `d1c4174 Initial commit`
- VPS: `87.106.22.98`
- Deploy path on VPS: `/opt/kbai-license-server`
- Public hostname now intended for this app: `app.automateki.de`
- App health check works at the origin and public DNS now points `app.automateki.de` to `87.106.22.98`

## What Was Built and Deployed

- Built a FastAPI license server for a self-hosted KnowledgeBase AI app.
- Purpose:
  - centralize Polar billing/subscription checks
  - receive Polar webhooks
  - create Polar checkout sessions
  - activate and validate local licenses for customer installations
  - enforce one monthly subscription per customer workspace
- Stack:
  - FastAPI
  - PostgreSQL
  - SQLAlchemy
  - Alembic
  - `polar-sdk`
  - Docker
  - Caddy
- Main API routes:
  - `GET /health`
  - `POST /billing/checkout`
  - `POST /billing/webhook/polar`
  - `POST /billing/sync`
  - `POST /license/activate`
  - `POST /license/validate`
  - `POST /license/deactivate`
  - `GET /license/status/{workspace_id}`
- Project includes:
  - Dockerized deployment
  - Alembic migration for `customers`, `activations`, `webhook_events`
  - tests for activate/validate/webhook/sync
  - VPS helper scripts
  - README for local/dev/prod setup

## What Was Done on GitHub and VPS

- Created and pushed the repo to GitHub.
- Deployed the app to the VPS at `/opt/kbai-license-server`.
- Old `price-alarm` app stack was removed from the VPS.
- New Docker stack is running:
  - `kbai-license-server-api-1`
  - `kbai-license-server-caddy-1`
  - `kbai-license-server-db-1`
- Caddy is serving the app and terminates HTTPS.
- The VPS `.env` was updated to use:
  - `APP_DOMAIN=app.automateki.de`
  - `POLAR_SUCCESS_URL=https://app.automateki.de/`
  - `POLAR_RETURN_URL=https://app.automateki.de/`
- Current VPS `.env` status:
  - `POLAR_SERVER=production`
  - `POLAR_ACCESS_TOKEN=<redacted>`
  - `POLAR_WEBHOOK_SECRET=<redacted>`
  - `POLAR_MONTHLY_PRODUCT_ID=replace-with-real-polar-monthly-product-id`
  - `POSTGRES_*` and `JWT_SECRET` are present with real generated values on the server
- Important: real DB/JWT secrets exist on the VPS, but Polar config is not fully finished.

## Current Known State

- Public DNS:
  - authoritative and public resolvers now return `app.automateki.de -> 87.106.22.98`
- Verified working checks:
  - `https://app.automateki.de/health`
  - `https://app.automateki.de/license/status/bootstrap-workspace`
- The old hostname `app.price-alarm.com` is no longer intended to be active for this app.
- Caddy is configured dynamically from `APP_DOMAIN`, so domain changes are driven by the VPS `.env`, not hardcoded in app code.

## What Codex in VSCode Should Do Next

- Finish Polar production configuration on the VPS:
  - set real `POLAR_ACCESS_TOKEN`
  - set real `POLAR_WEBHOOK_SECRET`
  - set real `POLAR_MONTHLY_PRODUCT_ID`
- Verify whether `POLAR_WEBHOOK_SECRET` matches the actual Polar webhook endpoint secret for `https://app.automateki.de/billing/webhook/polar`
- Confirm `POLAR_SUCCESS_URL` and `POLAR_RETURN_URL` should remain `https://app.automateki.de/` or change to app-specific callback URLs
- After updating Polar env values on the VPS:
  - restart the stack with `docker compose up -d`
  - test `POST /billing/sync` with an admin JWT
  - test `POST /billing/checkout`
  - send or receive a real `customer.state_changed` webhook from Polar
  - test `POST /license/activate`
  - test `POST /license/validate`
- Update README/examples if needed so docs match the final production hostname `app.automateki.de` instead of the earlier placeholder domain text

## Validation Checklist for the Next Engineer

- Confirm on VPS:
  - `cd /opt/kbai-license-server && docker compose ps`
- Confirm public health:
  - `curl https://app.automateki.de/health`
- Confirm app status route:
  - `curl https://app.automateki.de/license/status/bootstrap-workspace`
- Confirm billing/admin auth flow:
  - generate JWT signed with VPS `JWT_SECRET`
  - call `POST /billing/sync`
- Confirm Polar integration:
  - webhook endpoint registered in Polar
  - checkout session creates successfully
  - webhook updates local billing state
  - license validation only allows active subscribed workspaces

## Assumptions

- This service is the backend license/billing server for an AI-built KnowledgeBase app made in VSCode with Codex.
- The server should stay on `87.106.22.98`.
- `app.automateki.de` is now the canonical hostname for this service.
- Remaining work is mostly operational Polar configuration, not new backend feature implementation.
