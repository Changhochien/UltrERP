#!/bin/bash
# setup-skills.sh — Register UltrERP skills with Claude Code
# Run this after cloning the repo, or any time skills are added/updated.
#
# Usage:
#   ./setup-skills.sh              # interactive (default)
#   ./setup-skills.sh --force     # overwrite existing skill links
#   ./setup-skills.sh --dry-run   # show what would be linked without linking

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.claude/skills"
DEST_DIR="${HOME}/.claude/skills/UltrERP"
FORCE=false
DRYRUN=false

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)  FORCE=true; shift ;;
    --dry-run) DRYRUN=true; shift ;;
    --help)
      echo "Usage: $0 [--force] [--dry-run]"
      echo "  --force   Overwrite existing skill symlinks"
      echo "  --dry-run Show what would be linked without linking"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Skills that live in this repo
SKILLS=(
  "UltrERP-init"
  "UltrERP-ops"
  "UltrERP-migrate"
  "UltrERP-dump-import"
)

echo "=== UltrERP Skill Installer ==="
echo "Source: ${SKILLS_DIR}"
echo "Destination: ${DEST_DIR}"
echo ""

# Check Claude Code skills directory exists
if [[ ! -d "${HOME}/.claude/skills" ]]; then
  echo "Creating ~/.claude/skills/"
  if [[ "$DRYRUN" == "true" ]]; then
    echo "  [dry-run] would create ~/.claude/skills/"
  else
    mkdir -p "${HOME}/.claude/skills"
  fi
fi

# Check skills exist in repo
MISSING=()
for skill in "${SKILLS[@]}"; do
  if [[ ! -d "${SKILLS_DIR}/${skill}" ]]; then
    MISSING+=("$skill")
  fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "ERROR: Missing skills in ${SKILLS_DIR}: ${MISSING[*]}"
  echo "Available:"
  ls "${SKILLS_DIR}/"
  exit 1
fi

# Create per-skill symlinks under UltrERP/ namespace
LINK_DIR="${DEST_DIR}"
if [[ "$DRYRUN" == "true" ]]; then
  echo "  [dry-run] would create directory: ${LINK_DIR}"
else
  mkdir -p "${LINK_DIR}"
fi

for skill in "${SKILLS[@]}"; do
  SRC="${SKILLS_DIR}/${skill}"
  DST="${LINK_DIR}/${skill}"

  if [[ -L "$DST" && "$FORCE" == "false" ]]; then
    CURRENT=$(readlink "$DST")
    if [[ "$CURRENT" == "$SRC" ]]; then
      echo "  [skip] ${skill} — already linked correctly"
      continue
    else
      echo "  [skip] ${skill} — already linked to different source: ${CURRENT}"
      continue
    fi
  fi

  if [[ "$DRYRUN" == "true" ]]; then
    echo "  [dry-run] would link: ${DST} → ${SRC}"
  else
    if [[ -L "$DST" || -e "$DST" ]]; then
      if [[ "$FORCE" == "true" ]]; then
        rm -rf "$DST"
        echo "  [replace] ${skill}"
      else
        echo "  [skip] ${skill} — exists (use --force to replace)"
        continue
      fi
    fi
    ln -s "$SRC" "$DST"
    echo "  [linked] ${skill}"
  fi
done

echo ""
echo "Done. Available skills:"
for skill in "${SKILLS[@]}"; do
  echo "  /${skill}"
done
echo ""
echo "Restart Claude Code (or a new session) for skills to appear."
