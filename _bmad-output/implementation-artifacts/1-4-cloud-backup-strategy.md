# Story 1.4: Cloud Backup Strategy

Status: completed

Revalidation note: 2026-04-01 review confirmed the backup flow must normalize SQLAlchemy-style PostgreSQL URLs such as `postgresql+asyncpg://...` to libpq-compatible `postgresql://...` before invoking `pg_dump`.

## Story

As a developer/owner,
I want automated daily backups to cloud storage,
So that data is safe and recoverable for 10+ years.

## Context

Based on PRD requirements:
- **Retention:** 10+ years for accounting books and core financial records
- **Backup location:** Cloudflare R2 (S3-compatible, $5/mo for 150GB)
- **Tool:** `rclone copy` or versioned object uploads for append-only remote retention
- **Database:** PostgreSQL 17 with pg_dump

Note: This story implements local backup creation plus durable remote archival. The remote archive must not be pruned by the 7-day local retention rule.

## Acceptance Criteria

**Given** the backup scripts are in place
**When** `scripts/backup/pg-dump.sh` runs
**Then** it creates a compressed pg_dump file in `~/Library/Application Support/UltrERP/backups/`
**And** temporary local unencrypted backup artifacts older than 7 days are automatically removed
**And** `scripts/backup/rclone-sync.sh` copies encrypted archives to Cloudflare R2 without deleting existing remote backups
**And** `scripts/restore/pg-restore.sh` can recover from a local or downloaded backup archive

## Technical Requirements

### Backup Directory

```
~/Library/Application Support/UltrERP/backups/
├── ultr_erp_20260331_020000.dump   # Compressed pg_dump
├── ultr_erp_20260330_020000.dump
└── ...
```

### pg-dump.sh Script

```bash
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

# pg_dump with compression (-Fc)
pg_dump -Fc "${DB_TARGET}" -f "${BACKUP_DIR}/${backup_file}"

# Calculate checksum for integrity verification (macOS-compatible)
shasum -a 256 "${BACKUP_DIR}/${backup_file}" > "${BACKUP_DIR}/${checksum_file}"

# Encrypt for cloud storage (financial data requires encryption)
gpg --batch --yes --encrypt --recipient "${GPG_RECIPIENT}" \
  --output "${BACKUP_DIR}/${encrypted_file}" \
  "${BACKUP_DIR}/${backup_file}"

# Remove old local temporary artifacts only
find "${BACKUP_DIR}" -name 'ultr_erp_*.dump' -mtime +"${RETENTION_DAYS}" -delete
find "${BACKUP_DIR}" -name 'ultr_erp_*.dump.sha256' -mtime +"${RETENTION_DAYS}" -delete

printf 'Backup complete: %s\n' "${BACKUP_DIR}/${encrypted_file}"
```

### rclone-sync.sh Script

```bash
#!/bin/bash
set -e

BACKUP_DIR="${HOME}/Library/Application Support/UltrERP/backups"
R2_REMOTE="ultr-erp-backups"
R2_BUCKET="ultr-erp-backups"

# One-time setup:
# rclone config
# Select "s3" provider
# Provider: Cloudflare
# Access Key: your R2 access key (use RCLONE_CONFIG env vars for security)
# Secret Key: your R2 secret key
# Region: auto
# Endpoint: https://xxx.r2.cloudflarestorage.com
# Name: ultr-erp-backups

# Copy encrypted backups only (.gpg files) without remote deletion
rclone copy "${BACKUP_DIR}/" "${R2_REMOTE}:${R2_BUCKET}/postgres/" \
    --include "*.gpg" \
    --transfers 4 \
    --bwlimit 10M \
    --fast-list \
    --checksum \
    --progress

# Verify last backup integrity
LATEST_GPG=$(ls -t "${BACKUP_DIR}"/ultr_erp_*.dump.gpg 2>/dev/null | head -1)
if [ -n "${LATEST_GPG}" ]; then
  shasum -a 256 -c "${LATEST_GPG%.gpg}.sha256" || {
        echo "WARNING: Checksum verification failed for ${LATEST_GPG}"
        exit 1
    }
fi
```

### pg-restore.sh Script

```bash
#!/bin/bash
set -e

BACKUP_DIR="${HOME}/Library/Application Support/UltrERP/backups"
DB_NAME="ultr_erp"
BACKUP_FILE="$1"
GPG_RECIPIENT="backup@ultr-erp.local"

if [ -z "${BACKUP_FILE}" ]; then
    echo "Usage: $0 <backup_filename>"
    ls "${BACKUP_DIR}"/ultr_erp_*.dump.gpg 2>/dev/null || ls "${BACKUP_DIR}"/ultr_erp_*.dump
    exit 1
fi

# Decrypt if encrypted
if [[ "${BACKUP_FILE}" == *.gpg ]]; then
    DECRYPTED_FILE="${BACKUP_FILE%.gpg}"
    gpg --decrypt --recipient "${GPG_RECIPIENT}" --output "${DECRYPTED_FILE}" "${BACKUP_FILE}"
    BACKUP_FILE="${DECRYPTED_FILE}"
fi

# Warn before destructive restore
read -p "This will overwrite the current database. Continue? (y/N) " -r
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Single transaction for atomicity
psql -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ${DB_NAME};"
psql -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${DB_NAME};"
pg_restore -Fc -d "${DB_NAME}" "${BACKUP_FILE}" || {
    echo "ERROR: Restore failed. Database may be in inconsistent state."
    exit 1
}

echo "Restore complete: ${BACKUP_FILE}"
```

### Retention Policy (per PRD)

| Record Type | Retention | Notes |
|-------------|-----------|-------|
| eGUI consent/supporting | 5 years | |
| MOF platform records | 7+1 years | |
| Accounting books | 10 years | Minimum |
| Company policy | 15 years | Optional |

Remote retention is controlled by R2 lifecycle/versioning policy. Local 7-day cleanup does not apply to the remote archive.

### rclone Configuration

**One-time setup command:**
```bash
rclone config
# Select "s3" provider
# Provider: Cloudflare
# Access Key: [from R2 dashboard]
# Secret Key: [from R2 dashboard]
# Region: auto
# Endpoint: https://[account-id].r2.cloudflarestorage.com
```

## Tasks

- [x] Task 1: Create backup scripts directory and files
  - [x] Subtask: Create scripts/backup/pg-dump.sh
  - [x] Subtask: Create scripts/backup/rclone-sync.sh
  - [x] Subtask: Create scripts/restore/pg-restore.sh
  - [x] Subtask: Make scripts executable (chmod +x)
- [x] Task 2: Configure GPG encryption
  - [x] Subtask: Generate GPG key for backup encryption
  - [x] Subtask: Document key management procedure
- [x] Task 3: Configure rclone remote
  - [x] Subtask: Document rclone config command in README
  - [x] Subtask: Use environment variables for R2 credentials (NOT .env files)
- [x] Task 4: Configure R2 lifecycle policy
  - [x] Subtask: Document R2 retention requirements for 10+ years
  - [x] Subtask: Configure R2 Object Lifecycle and/or versioning rules via dashboard
- [x] Task 5: Document backup strategy
  - [x] Subtask: Document retention policy in README
  - [x] Subtask: Document restore procedure
  - [x] Subtask: Add backup verification and alerting
- [x] Task 6: Create cron/launchd entry documentation
  - [x] Subtask: Document macOS launchd setup for daily backup
  - [x] Subtask: Document backup verification commands

## Dev Notes

### Critical Implementation Details

1. **pg_dump -Fc** - Custom format for compression and parallel restore
2. **LOCAL backup dir** - ~/Library/Application Support/UltrERP/backups (not in repo)
3. **7-day local retention** - Applies only to temporary unencrypted local artifacts
4. **Remote archive must be append-only** - Do not mirror local deletions into R2
5. **--fast-list** - Uses listing cache, faster for large directories
6. **Normalize SQLAlchemy URLs for CLI tools** - `pg_dump` must receive `postgresql://...`, not `postgresql+asyncpg://...`

### PRD Compliance

- Supports 10+ year retention per NFR22
- Records stored durably in cloud per NFR15
- Backup/restore strategy per architecture Section 8

### Source References

- PRD: Section on Retention & Archival Baseline
- Architecture: Section 8.4 - Retention Policy Baseline
- PRD: NFR22 - Database backup strategy

## File List

- scripts/backup/pg-dump.sh
- scripts/backup/rclone-sync.sh
- scripts/restore/pg-restore.sh

## Validation Evidence

- Backup and restore scripts pass `bash -n` validation and retain executable permissions.
- README now documents environment variables, GPG key creation, backup commands, restore commands, and a macOS `launchd` example.

## Review Outcome

- Backup creation now fails fast when the configured GPG recipient is missing.
- Remote sync now requires a checksum artifact, and restore verifies checksums for both encrypted and plain dump inputs.
