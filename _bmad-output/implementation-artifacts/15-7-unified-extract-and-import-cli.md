# Story 15.7: Unified Extract + Import CLI

Status: done

## Story

As an operator who wants to import legacy data from a raw SQL dump,
I want a single CLI entry point that can both decode the dump into CSVs and run the full import pipeline,
So that the full workflow (raw SQL → canonical DB) is unified under one tool and one skill.

## Story Summary

The upstream SQL extractor (`legacy-migration-pipeline/src/`) and the downstream import CLI (`backend/domains/legacy_import/cli.py`) were two separate tools. This story consolidates them:

- **Upstream modules moved** into `backend/domains/legacy_import/` as `extractor_detector.py`, `extractor_parser.py`, `extractor_cleaner.py`
- **New `extract` subcommand** added to the import CLI as phase 0
- **Skill docs updated** to describe the full pipeline from raw SQL dump to validated canonical import

## Acceptance Criteria

**AC1:** The `extract` subcommand is the first phase of the CLI
**Given** an operator has a raw SQL dump file
**When** they run `legacy-import extract --input dump.sql --output extracted_data/`
**Then** the CLI decodes the dump into CSV files using auto-detected Big5-HKSCS encoding and mojibake cleaning
**And** the output directory contains one CSV per table matching the source dump

**AC2:** Extractor modules are importable from the backend package
**Given** the backend Python environment is active
**When** the operator imports `from domains.legacy_import import extractor_parser, extractor_detector, extractor_cleaner`
**Then** all three modules load without errors
**And** `uv run python -m domains.legacy_import.cli extract --help` shows the extract subcommand

**AC3:** The legacy-import skill covers the full pipeline including extract
**Given** the `/legacy-import` skill is loaded by an AI agent
**When** the operator asks to import legacy data from a raw SQL dump
**Then** the skill guides them through `extract` (phase 0) as the entry point
**And** the command map documents `--input`, `--output`, `--format`, and `--encoding` flags

**AC4:** Re-running extract produces the same table count
**Given** a SQL dump has been extracted once
**When** the operator re-runs `extract` with the same input and output path
**Then** the output directory contains the same number of CSV files as the original extraction
**And** no error is raised (idempotent overwrite)

**AC5:** The original upstream extractor directory is preserved
**Given** the consolidation is complete
**When** the operator inspects `legacy-migration-pipeline/src/`
**Then** the original Python modules are still present (not deleted)
**And** no git history is broken

## Tasks / Subtasks

- [x] **Task 1: Move upstream extractor modules into backend package**
  - [x] Copy `detector.py`, `parser.py`, `cleaner.py` from `legacy-migration-pipeline/src/` to `backend/domains/legacy_import/` with renamed filenames (`extractor_detector.py`, `extractor_parser.py`, `extractor_cleaner.py`)
  - [x] Import all three in `cli.py`

- [x] **Task 2: Add `extract` subcommand to the import CLI**
  - [x] Add `extract` subparser with `--input`, `--output`, `--format`, `--encoding` flags
  - [x] Implement `_run_extract` function using `SQLDumpParser` + `MojibakeCleaner`
  - [x] Wire into main dispatch (if-elif chain)

- [x] **Task 3: Update skill documentation for extract phase**
  - [x] Update `SKILL.md` description to mention SQL dump extraction; add `extract` to operating rules and confirmation checklist
  - [x] Update `command-map.md` with `extract` as phase 0, including all flags
  - [x] Sync changes to both `.claude/skills/legacy-import/` and `.agents/skills/legacy-import/`

- [x] **Task 4: Verify end-to-end**
  - [x] `uv run python -m domains.legacy_import.cli --help` shows `extract` as first subcommand
  - [x] `extract --help` shows correct flags
  - [x] Live extraction of `cao50001.sql` produces 94 tables, ~1.1M rows matching original extractor output

## Validation

Validated on 2026-04-05 via:
- `uv run python -m domains.legacy_import.cli extract --help` — extract subcommand visible with correct flags
- Live extraction of `/Volumes/2T_SSD_App/Projects/UltrERP/legacy data/cao50001.sql` → 94 tables, 1,157,329 total rows
- Table count and row counts match original `legacy-migration-pipeline/src/cli.py` output exactly
- Skill slash command `/legacy-import` loads with updated description covering SQL dump extraction
- Both `.claude/skills/legacy-import/` and `.agents/skills/legacy-import/` in sync

## Notes

- `[project.scripts]` entry point was not added — the backend uses `package = false` in `[tool.uv]` which is incompatible with hatchling script entry points. Module invocation (`uv run python -m domains.legacy_import.cli`) remains the documented form.
- The `legacy-migration-pipeline/src/` directory was preserved (not deleted) to avoid breaking git history.
