#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${1:-$ROOT_DIR/dist/hosted-installers}"
TOKEN="${QUICKSTART_LICENSE_SERVER_ADMIN_TOKEN:-}"

[ -n "$TOKEN" ] || {
  printf '[ERROR] QUICKSTART_LICENSE_SERVER_ADMIN_TOKEN is required.\n' >&2
  exit 1
}

mkdir -p "$OUTPUT_DIR"

sed -e "s|__LICENSE_SERVER_ADMIN_TOKEN__|$TOKEN|g" -e "s|__INSTALLER_RENDERED__|rendered|g" "$ROOT_DIR/quickstart/install.sh" > "$OUTPUT_DIR/install.sh"
sed -e "s|__LICENSE_SERVER_ADMIN_TOKEN__|$TOKEN|g" -e "s|__INSTALLER_RENDERED__|rendered|g" "$ROOT_DIR/quickstart/install.ps1" > "$OUTPUT_DIR/install.ps1"
chmod +x "$OUTPUT_DIR/install.sh"

printf '[INFO] Hosted installer files rendered to %s\n' "$OUTPUT_DIR"
