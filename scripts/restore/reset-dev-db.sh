#!/bin/bash
set -euo pipefail

normalize_pg_cli_target() {
  local target="$1"

  if [[ "${target}" =~ ^postgresql\+[^:]+:// ]]; then
    printf 'postgresql://%s\n' "${target#*://}"
    return
  fi

  printf '%s\n' "${target}"
}

database_name_from_target() {
  local target="$1"
  local trimmed_target="${target%%\?*}"

  if [[ "${trimmed_target}" =~ ^postgresql:// ]]; then
    printf '%s\n' "${trimmed_target##*/}"
    return
  fi

  printf '%s\n' "${trimmed_target}"
}

database_owner_from_target() {
  local target="$1"
  local trimmed_target="${target%%\?*}"
  local without_scheme="${trimmed_target#postgresql://}"
  local userinfo="${without_scheme%%@*}"
  local username="${userinfo%%:*}"

  if [[ "${trimmed_target}" =~ ^postgresql:// && "${without_scheme}" == *"@"* && -n "${username}" ]]; then
    printf '%s\n' "${username}"
    return
  fi

  printf '%s\n' "${ULTR_ERP_DB_OWNER:-${TARGET_DB_NAME}}"
}

maintenance_target_from_db_target() {
  local db_target="$1"
  local maintenance_db="${PG_MAINTENANCE_DB:-postgres}"
  local trimmed_target="${db_target%%\?*}"
  local query_suffix=""

  if [[ "${db_target}" == *\?* ]]; then
    query_suffix="?${db_target#*\?}"
  fi

  if [[ "${trimmed_target}" =~ ^postgresql:// ]]; then
    printf '%s/%s%s\n' "${trimmed_target%/*}" "${maintenance_db}" "${query_suffix}"
    return
  fi

  printf '%s\n' "${maintenance_db}"
}

quote_pg_identifier() {
  printf '"%s"' "${1//\"/\"\"}"
}

usage() {
  cat <<'EOF'
Usage: scripts/restore/reset-dev-db.sh [--yes] [--skip-bootstrap]

Drops and recreates the configured development database, applies Alembic migrations,
and by default seeds non-sensitive app settings plus the default dev users.

Environment:
  DATABASE_URL         Preferred database target.
  ULTR_ERP_DB_NAME     Fallback database name when DATABASE_URL is unset.
  PG_MAINTENANCE_DB    Maintenance database used for DROP/CREATE (default: postgres).

Options:
  --yes               Skip the destructive-operation confirmation prompt.
  --skip-bootstrap    Leave the database migrated but do not seed settings/dev users.
  --help              Show this help text.
EOF
}

confirm=false
bootstrap=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes)
      confirm=true
      ;;
    --skip-bootstrap)
      bootstrap=false
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

raw_db_target="${DATABASE_URL:-${ULTR_ERP_DB_NAME:-ultr_erp}}"
DB_TARGET="$(normalize_pg_cli_target "${raw_db_target}")"
TARGET_DB_NAME="$(database_name_from_target "${DB_TARGET}")"
MAINTENANCE_TARGET="$(maintenance_target_from_db_target "${DB_TARGET}")"
TARGET_DB_OWNER="$(database_owner_from_target "${DB_TARGET}")"
quoted_db_name="$(quote_pg_identifier "${TARGET_DB_NAME}")"
quoted_db_owner="$(quote_pg_identifier "${TARGET_DB_OWNER}")"

echo "Target database : ${TARGET_DB_NAME}"
echo "Database owner  : ${TARGET_DB_OWNER}"
echo "DB target       : ${DB_TARGET}"
echo "Bootstrap data  : ${bootstrap}"
echo "Steps           : drop/create -> alembic upgrade head -> optional dev bootstrap"

if [[ "${confirm}" != true ]]; then
  read -r -p "This will delete and recreate '${TARGET_DB_NAME}'. Continue? (y/N) " reply
  if [[ ! "${reply}" =~ ^[Yy]$ ]]; then
    echo "Reset cancelled."
    exit 1
  fi
fi

psql "${MAINTENANCE_TARGET}" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ${quoted_db_name} WITH (FORCE);"
psql "${MAINTENANCE_TARGET}" -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${quoted_db_name} OWNER ${quoted_db_owner};"

pushd "${REPO_ROOT}/backend" >/dev/null
uv run alembic -c ../migrations/alembic.ini upgrade head

if [[ "${bootstrap}" == true ]]; then
  uv run python -m scripts.bootstrap_dev_database
fi

popd >/dev/null

echo "Development database reset complete: ${TARGET_DB_NAME}"