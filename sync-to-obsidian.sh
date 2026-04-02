#!/bin/bash
# Sync UltrERP artifacts to Obsidian vault
# Usage: ./sync-to-obsidian.sh

set -e

ULTRERP_ROOT="$(cd "$(dirname "$0")" && pwd)"
OBSIDIAN_VAULT="$HOME/Obsidian-note"

echo "Syncing UltrERP artifacts to Obsidian vault..."

# Sync _bmad-output
if [ -d "$ULTRERP_ROOT/_bmad-output" ]; then
    echo "  → Syncing _bmad-output..."
    rsync -av --delete \
        --exclude='*.log' \
        --exclude='.DS_Store' \
        "$ULTRERP_ROOT/_bmad-output/" "$OBSIDIAN_VAULT/UltrERP-bmad-output/"
fi

# Sync docs
if [ -d "$ULTRERP_ROOT/docs" ]; then
    echo "  → Syncing docs..."
    rsync -av --delete \
        --exclude='*.log' \
        --exclude='.DS_Store' \
        "$ULTRERP_ROOT/docs/" "$OBSIDIAN_VAULT/UltrERP-docs/"
fi

# Sync design-artifacts
if [ -d "$ULTRERP_ROOT/design-artifacts" ]; then
    echo "  → Syncing design-artifacts..."
    rsync -av --delete \
        --exclude='*.log' \
        --exclude='.DS_Store' \
        "$ULTRERP_ROOT/design-artifacts/" "$OBSIDIAN_VAULT/UltrERP-design-artifacts/"
fi

echo ""
echo "Sync complete! Run these commands to commit:"
echo "  cd $OBSIDIAN_VAULT"
echo "  git add -A && git commit -m 'Sync artifacts: $(date +%Y-%m-%d)' && git push"
