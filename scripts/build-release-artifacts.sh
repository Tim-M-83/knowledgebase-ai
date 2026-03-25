#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="${1:-$ROOT_DIR/dist}"
PACKAGE_DIR="$DIST_DIR/knowledgebase-ai"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    printf '[ERROR] Required command not found: %s\n' "$1" >&2
    exit 1
  }
}

copy_dir() {
  local source="$1"
  local target="$2"
  shift 2
  rsync -a "$@" "$source" "$target"
}

need_cmd rsync
need_cmd tar
need_cmd zip

rm -rf "$DIST_DIR"
mkdir -p "$PACKAGE_DIR"

copy_dir "$ROOT_DIR/backend/" "$PACKAGE_DIR/backend/" \
  --exclude='.pytest_cache' \
  --exclude='__pycache__' \
  --exclude='*.pyc'

copy_dir "$ROOT_DIR/frontend/" "$PACKAGE_DIR/frontend/" \
  --exclude='.next' \
  --exclude='node_modules' \
  --exclude='*.tsbuildinfo'

cp "$ROOT_DIR/docker-compose.yml" "$PACKAGE_DIR/docker-compose.yml"
cp "$ROOT_DIR/.env.example" "$PACKAGE_DIR/.env.example"
cp "$ROOT_DIR/README.md" "$PACKAGE_DIR/README.md"
cp "$ROOT_DIR/APP_DOKUMENTATION.md" "$PACKAGE_DIR/APP_DOKUMENTATION.md"
cp "$ROOT_DIR/How_To_Install.md" "$PACKAGE_DIR/How_To_Install.md"
copy_dir "$ROOT_DIR/quickstart/" "$PACKAGE_DIR/quickstart/"

find "$PACKAGE_DIR" -name '.DS_Store' -delete

(
  cd "$DIST_DIR"
  tar -czf knowledgebase-ai.tar.gz knowledgebase-ai
  zip -qr knowledgebase-ai.zip knowledgebase-ai
)

printf '[INFO] Release artifacts created in %s\n' "$DIST_DIR"
