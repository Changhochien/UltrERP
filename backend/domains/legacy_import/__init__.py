"""Legacy import domain package."""

from __future__ import annotations

from domains.legacy_import.canonical import CanonicalImportResult, run_canonical_import
from domains.legacy_import.mapping import (
    CORRECTED_ORPHAN_CODE_BASELINE,
    CORRECTED_ORPHAN_ROW_BASELINE,
    UNKNOWN_PRODUCT_CODE,
    ProductMappingBatchResult,
    ProductMappingRecord,
    ProductMappingSeedResult,
    seed_product_code_mappings,
)
from domains.legacy_import.normalization import (
    NormalizationBatchResult,
    deterministic_legacy_uuid,
    normalize_legacy_date,
    normalize_party_record,
    run_normalization,
)
from domains.legacy_import.staging import (
    DiscoveredLegacyTable,
    LegacySourceCompatibilityError,
    StageBatchResult,
    StageTableResult,
    discover_legacy_tables,
    parse_legacy_row,
    run_live_stage_import,
    run_stage_import,
)
from domains.legacy_import.validation import (
    ImportReplayMetadata,
    MigrationBatchValidationResult,
    MigrationValidationIssue,
    MigrationValidationReport,
    ProductMappingValidationSummary,
    StageReconciliationRow,
    ValidationStageFailure,
    validate_import_batch,
)

__all__ = [
    "CORRECTED_ORPHAN_CODE_BASELINE",
    "CORRECTED_ORPHAN_ROW_BASELINE",
    "CanonicalImportResult",
    "DiscoveredLegacyTable",
    "NormalizationBatchResult",
    "ProductMappingBatchResult",
    "ProductMappingRecord",
    "ProductMappingSeedResult",
    "ProductMappingValidationSummary",
    "StageBatchResult",
    "StageReconciliationRow",
    "StageTableResult",
    "UNKNOWN_PRODUCT_CODE",
    "ImportReplayMetadata",
    "LegacySourceCompatibilityError",
    "MigrationBatchValidationResult",
    "MigrationValidationIssue",
    "MigrationValidationReport",
    "ValidationStageFailure",
    "deterministic_legacy_uuid",
    "discover_legacy_tables",
    "normalize_legacy_date",
    "normalize_party_record",
    "parse_legacy_row",
    "run_canonical_import",
    "run_live_stage_import",
    "run_normalization",
    "run_stage_import",
    "validate_import_batch",
    "seed_product_code_mappings",
]
