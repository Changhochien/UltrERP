#!/bin/bash
set -euo pipefail

BACKUP_DIR="${HOME}/Library/Application Support/UltrERP/backups"
RCLONE_REMOTE="${RCLONE_REMOTE:-ultr-erp-backups}"
R2_BUCKET="${R2_BUCKET:-ultr-erp-backups}"

latest_archive="$(find "${BACKUP_DIR}" -maxdepth 1 -name 'ultr_erp_*.dump.gpg' -print | sort | tail -n 1)"

if [[ -z "${latest_archive}" ]]; then
  echo "No encrypted backups found in ${BACKUP_DIR}" >&2
  exit 1
fi

checksum_file="${latest_archive%.gpg}.sha256"

if [[ ! -f "${checksum_file}" ]]; then
  echo "Checksum file not found for ${latest_archive}" >&2
  exit 1
fi

shasum -a 256 -c "${checksum_file}"

rclone copy "${BACKUP_DIR}/" "${RCLONE_REMOTE}:${R2_BUCKET}/postgres/" \
  --include 'ultr_erp_*.dump.gpg' \
  --include 'ultr_erp_*.dump.sha256' \
  --checkers 4 \
  --transfers 4 \
  --bwlimit 10M \
  --fast-list \
  --checksum

printf 'Remote archive sync complete: %s:%s/postgres/\n' "${RCLONE_REMOTE}" "${R2_BUCKET}"
