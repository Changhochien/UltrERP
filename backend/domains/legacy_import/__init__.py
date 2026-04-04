"""Legacy import domain package."""

from domains.legacy_import.staging import (
	DiscoveredLegacyTable,
	StageBatchResult,
	StageTableResult,
	discover_legacy_tables,
	parse_legacy_row,
	run_stage_import,
)

__all__ = [
	"DiscoveredLegacyTable",
	"StageBatchResult",
	"StageTableResult",
	"discover_legacy_tables",
	"parse_legacy_row",
	"run_stage_import",
]