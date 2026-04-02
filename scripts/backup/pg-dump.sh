#!/bin/bash
set -euo pipefail

BACKUP_DIR="${HOME}/Library/Application Support/UltrERP/backups"

normalize_pg_cli_target() {
  local target="$1"

  # PostgreSQL CLI tools understand libpq URLs, not SQLAlchemy dialect URLs.
  if [[ "${target}" =~ ^postgresql\+[^:]+:// ]]; then
    printf 'postgresql://%s\n' "${target#*://}"
    return
  fi

  printf '%s\n' "${target}"
}

raw_db_target="${DATABASE_URL:-${ULTR_ERP_DB_NAME:-ultr_erp}}"
DB_TARGET="$(normalize_pg_cli_target "${raw_db_target}")"
RETENTION_DAYS="${ULTR_ERP_BACKUP_RETENTION_DAYS:-7}"
GPG_RECIPIENT="${BACKUP_GPG_RECIPIENT:-backup@ultr-erp.local}"

mkdir -p "${BACKUP_DIR}"

gpg --list-keys "${GPG_RECIPIENT}" >/dev/null 2>&1 || {
  echo "GPG recipient not found: ${GPG_RECIPIENT}" >&2
  exit 1
}

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_file="ultr_erp_${timestamp}.dump"
checksum_file="${backup_file}.sha256"
encrypted_file="${backup_file}.gpg"

pg_dump -Fc "${DB_TARGET}" -f "${BACKUP_DIR}/${backup_file}"
shasum -a 256 "${BACKUP_DIR}/${backup_file}" > "${BACKUP_DIR}/${checksum_file}"
gpg --batch --yes --encrypt --recipient "${GPG_RECIPIENT}" \
  --output "${BACKUP_DIR}/${encrypted_file}" \
  "${BACKUP_DIR}/${backup_file}"

find "${BACKUP_DIR}" -name 'ultr_erp_*.dump' -mtime +"${RETENTION_DAYS}" -delete
find "${BACKUP_DIR}" -name 'ultr_erp_*.dump.sha256' -mtime +"${RETENTION_DAYS}" -delete

printf 'Backup complete: %s\n' "${BACKUP_DIR}/${encrypted_file}"
