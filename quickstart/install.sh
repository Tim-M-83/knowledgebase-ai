#!/usr/bin/env bash
set -euo pipefail

APP_NAME="KnowledgeBase AI"
INSTALL_DIR="${INSTALL_DIR:-knowledgebase-ai}"
ARCHIVE_URL="https://github.com/Tim-M-83/knowledgebase-ai/releases/latest/download/knowledgebase-ai.tar.gz"
LICENSE_SERVER_ADMIN_TOKEN="__LICENSE_SERVER_ADMIN_TOKEN__"
INSTALLER_RENDER_MARKER="__INSTALLER_RENDERED__"
TMP_DIR=''

info() {
  printf '\n[INFO] %s\n' "$1"
}

warn() {
  printf '\n[WARN] %s\n' "$1" >&2
}

fail() {
  printf '\n[ERROR] %s\n' "$1" >&2
  exit 1
}

cleanup_tmp_dir() {
  if [ -n "${TMP_DIR:-}" ] && [ -d "${TMP_DIR:-}" ]; then
    rm -rf "$TMP_DIR"
  fi
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

check_docker() {
  need_cmd docker
  docker info >/dev/null 2>&1 || fail 'Docker is installed but not running. Start Docker Desktop or Docker Engine first.'
  docker compose version >/dev/null 2>&1 || fail 'Docker Compose plugin is required. Install Docker Desktop or a recent Docker Engine with docker compose support.'
}

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi

  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | awk 'NR > 1 {print $4}' | grep -Eq "(^|:)$port$"
    return $?
  fi

  if command -v netstat >/dev/null 2>&1; then
    netstat -an 2>/dev/null | grep -E "[\.:]$port[[:space:]].*(LISTEN|LISTENING)" >/dev/null 2>&1
    return $?
  fi

  return 1
}

check_ports() {
  local port
  for port in 3000 8000 5432 6379; do
    if port_in_use "$port"; then
      fail "Port $port is already in use. Stop the conflicting service before installing ${APP_NAME}."
    fi
  done
}

generate_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import secrets; print(secrets.token_hex(32))'
    return
  fi

  if command -v od >/dev/null 2>&1; then
    dd if=/dev/urandom bs=32 count=1 2>/dev/null | od -An -tx1 | tr -d ' \n'
    return
  fi

  fail 'Unable to generate a secure random secret. Install openssl, python3, or od.'
}

generate_workspace_id() {
  printf 'workspace-%s' "$(generate_secret | cut -c1-32)"
}

set_env_value() {
  local file="$1"
  local key="$2"
  local value="$3"
  local tmp
  tmp="$(mktemp)"
  awk -v key="$key" -v value="$value" '
    BEGIN { replaced = 0 }
    index($0, key "=") == 1 {
      print key "=" value
      replaced = 1
      next
    }
    { print }
    END {
      if (replaced == 0) {
        print key "=" value
      }
    }
  ' "$file" > "$tmp"
  mv "$tmp" "$file"
}

download_release() {
  local tmp_dir="$1"
  local archive_path="$tmp_dir/knowledgebase-ai.tar.gz"

  info "Downloading the latest stable release from GitHub"
  if ! curl -fsSL "$ARCHIVE_URL" -o "$archive_path"; then
    fail 'Could not download the latest release archive. Make sure the repository is public and the release asset exists.'
  fi

  tar -xzf "$archive_path" -C "$tmp_dir"
  [ -d "$tmp_dir/knowledgebase-ai" ] || fail 'The downloaded release archive is missing the expected knowledgebase-ai folder.'
}

wait_for_api() {
  local max_attempts=120
  local attempt=1

  info 'Waiting for the API to become healthy'
  while [ "$attempt" -le "$max_attempts" ]; do
    if curl -fsSL http://localhost:8000/health >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
    attempt=$((attempt + 1))
  done

  return 1
}

extract_bootstrap_credentials() {
  local project_dir="$1"
  local email=''
  local password=''
  local max_attempts=30
  local attempt=1
  local logs=''

  while [ "$attempt" -le "$max_attempts" ]; do
    logs="$(cd "$project_dir" && docker compose logs api --no-color 2>&1 || true)"
    email="$(printf '%s\n' "$logs" | sed -n 's/^.*Email: \(.*\)$/\1/p' | tail -n 1)"
    password="$(printf '%s\n' "$logs" | sed -n 's/^.*Password: \(.*\)$/\1/p' | tail -n 1)"

    if [ -n "$email" ] && [ -n "$password" ]; then
      printf '%s\n%s\n' "$email" "$password"
      return 0
    fi

    sleep 2
    attempt=$((attempt + 1))
  done

  return 1
}

main() {
  local jwt_secret
  local secrets_key
  local workspace_id
  local creds
  local bootstrap_email=''
  local bootstrap_password=''

  [ "$INSTALLER_RENDER_MARKER" = 'rendered' ] || fail 'This installer template has not been rendered with a shared LICENSE_SERVER_ADMIN_TOKEN yet.'

  check_docker
  need_cmd curl
  need_cmd tar
  check_ports

  [ ! -e "$INSTALL_DIR" ] || fail "Target directory already exists: $INSTALL_DIR"

  TMP_DIR="$(mktemp -d)"
  trap cleanup_tmp_dir EXIT INT TERM

  download_release "$TMP_DIR"
  mv "$TMP_DIR/knowledgebase-ai" "$INSTALL_DIR"

  info "Preparing environment configuration"
  cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
  jwt_secret="$(generate_secret)"
  secrets_key="$(generate_secret)"
  workspace_id="$(generate_workspace_id)"

  set_env_value "$INSTALL_DIR/.env" 'JWT_SECRET' "$jwt_secret"
  set_env_value "$INSTALL_DIR/.env" 'SECRETS_ENCRYPTION_KEY' "$secrets_key"
  set_env_value "$INSTALL_DIR/.env" 'NEXT_PUBLIC_API_URL' 'http://localhost:8000'
  set_env_value "$INSTALL_DIR/.env" 'FRONTEND_URL' 'http://localhost:3000'
  set_env_value "$INSTALL_DIR/.env" 'LICENSE_SERVER_BASE_URL' 'https://app.automateki.de'
  set_env_value "$INSTALL_DIR/.env" 'LICENSE_SERVER_ADMIN_TOKEN' "$LICENSE_SERVER_ADMIN_TOKEN"
  set_env_value "$INSTALL_DIR/.env" 'LICENSE_COMPANY_NAME' 'KnowledgeBase AI'
  set_env_value "$INSTALL_DIR/.env" 'LICENSE_BILLING_EMAIL' ''
  set_env_value "$INSTALL_DIR/.env" 'LICENSE_WORKSPACE_ID' "$workspace_id"
  set_env_value "$INSTALL_DIR/.env" 'LICENSE_ENFORCEMENT_ENABLED' 'true'
  set_env_value "$INSTALL_DIR/.env" 'OPENAI_API_KEY' ''

  info "Starting Docker containers"
  (
    cd "$INSTALL_DIR"
    docker compose up -d --build
  )

  if ! wait_for_api; then
    fail "The API did not become healthy in time. Check logs with: cd $INSTALL_DIR && docker compose logs api"
  fi

  if creds="$(extract_bootstrap_credentials "$INSTALL_DIR")"; then
    bootstrap_email="$(printf '%s\n' "$creds" | sed -n '1p')"
    bootstrap_password="$(printf '%s\n' "$creds" | sed -n '2p')"
  else
    warn 'Bootstrap credentials were not found automatically in the API logs. You can inspect them manually with: docker compose logs api --no-color'
  fi

  printf '\n%s\n' '========================================================================'
  printf '%s installed successfully.\n' "$APP_NAME"
  printf 'Open: http://localhost:3000/login\n'
  printf 'Workspace ID: %s\n' "$workspace_id"
  if [ -n "$bootstrap_email" ] && [ -n "$bootstrap_password" ]; then
    printf 'Bootstrap email: %s\n' "$bootstrap_email"
    printf 'Bootstrap password: %s\n' "$bootstrap_password"
  fi
  printf 'Next steps:\n'
  printf '1. Open the login page and sign in with the bootstrap credentials above.\n'
  printf '2. Open Settings > License & Subscription.\n'
  printf '3. Click Buy / Renew Subscription, start the 7-day free trial or purchase, then activate the installation.\n'
  printf '4. Add your OpenAI API key later in Settings if you want to use OpenAI immediately.\n'
  printf '5. Keep this Workspace ID. To reuse the same Polar purchase after a reinstall, restore LICENSE_WORKSPACE_ID=%s in .env before restarting the API.\n' "$workspace_id"
  printf '%s\n\n' '========================================================================'
}

main "$@"
