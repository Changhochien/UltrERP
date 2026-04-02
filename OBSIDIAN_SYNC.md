# Obsidian Sync Setup

This project syncs artifacts to your Obsidian vault for cross-device knowledge access.

## Quick Start

```bash
# Run sync manually
./sync-to-obsidian.sh

# Commit to Obsidian vault
cd ~/Obsidian-note
git add -A && git commit -m "sync" && git push
```

## What's Synced

| UltrERP | Obsidian Vault |
|---------|----------------|
| `_bmad-output/` | `UltrERP-bmad-output/` |
| `docs/` | `UltrERP-docs/` |
| `design-artifacts/` | `UltrERP-design-artifacts/` |

## Cross-Device Setup

On another computer:

```bash
# 1. Clone UltrERP
git clone https://github.com/Changhochien/UltrERP.git

# 2. Clone Obsidian vault
gh repo clone Changhochien/Obsidian-note ~/Obsidian-note

# 3. Recreate symlinks
cd ~/Obsidian-note
ln -s ~/UltrERP/_bmad-output UltrERP-bmad-output
ln -s ~/UltrERP/docs UltrERP-docs
ln -s ~/UltrERP/design-artifacts UltrERP-design-artifacts
```

## Auto-Sync

A post-commit hook runs `./sync-to-obsidian.sh` after every UltrERP commit.
