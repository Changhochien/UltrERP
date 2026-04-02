#!/bin/bash
set -euo pipefail

BACKUP_DIR="${HOME}/Library/Application Support/UltrERP/backups"
GPG_RECIPIENT="${BACKUP_GPG_RECIPIENT:-backup@ultr-erp.local}"
input_path="${1:-}"

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

raw_db_target="${DATABASE_URL:-${ULTR_ERP_DB_NAME:-ultr_erp}}"
DB_TARGET="$(normalize_pg_cli_target "${raw_db_target}")"
TARGET_DB_NAME="$(database_name_from_target "${DB_TARGET}")"
MAINTENANCE_TARGET="$(maintenance_target_from_db_target "${DB_TARGET}")"

if [[ -z "${input_path}" ]]; then
  echo "Usage: $0 <backup-file>" >&2
  find "${BACKUP_DIR}" -maxdepth 1 \( -name 'ultr_erp_*.dump' -o -name 'ultr_erp_*.dump.gpg' \) -print | sort
  exit 1
fi

if [[ ! -f "${input_path}" ]]; then
  input_path="${BACKUP_DIR}/${input_path}"
fi

if [[ ! -f "${input_path}" ]]; then
  echo "Backup file not found: ${1}" >&2
  exit 1
fi

working_file="${input_path}"
temp_dir=""

cleanup() {
  if [[ -n "${temp_dir}" && -d "${temp_dir}" ]]; then
    rm -rf "${temp_dir}"
  fi
}

trap cleanup EXIT

if [[ "${input_path}" == *.gpg ]]; then
  temp_dir="$(mktemp -d)"
  working_file="${temp_dir}/$(basename "${input_path%.gpg}")"
  gpg --batch --yes --decrypt --recipient "${GPG_RECIPIENT}" --output "${working_file}" "${input_path}"
fi

checksum_file="${input_path%.gpg}.sha256"
if [[ -f "${checksum_file}" ]]; then
  restored_checksum="$(shasum -a 256 "${working_file}" | awk '{print $1}')"
  expected_checksum="$(awk '{print $1}' "${checksum_file}")"
  if [[ "${restored_checksum}" != "${expected_checksum}" ]]; then
    echo "Checksum verification failed for ${input_path}" >&2
    exit 1
  fi
fi

read -r -p "This will replace database '${TARGET_DB_NAME}'. Continue? (y/N) " reply
if [[ ! "${reply}" =~ ^[Yy]$ ]]; then
  echo "Restore cancelled."
  exit 1
fi

quoted_db_name="$(quote_pg_identifier "${TARGET_DB_NAME}")"

psql "${MAINTENANCE_TARGET}" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ${quoted_db_name};"
psql "${MAINTENANCE_TARGET}" -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${quoted_db_name};"
pg_restore -Fc -d "${DB_TARGET}" "${working_file}"

printf 'Restore complete: %s\n' "${working_file}"