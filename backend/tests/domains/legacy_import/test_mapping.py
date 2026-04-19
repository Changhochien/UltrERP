from decimal import Decimal

import pytest

from domains.legacy_import import mapping
from domains.legacy_import.mapping import (
    CORRECTED_ORPHAN_CODE_BASELINE,
    CORRECTED_ORPHAN_ROW_BASELINE,
    UNKNOWN_PRODUCT_CODE,
    ProductMappingReviewExportResult,
    seed_product_code_mappings,
)


class FakeMappingTransaction:
    def __init__(self, connection: "FakeMappingConnection") -> None:
        self.connection = connection

    async def __aenter__(self) -> "FakeMappingTransaction":
        self.connection.transaction_started = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            self.connection.transaction_committed = True
        else:
            self.connection.transaction_rolled_back = True
        return False


class FakeMappingConnection:
    def __init__(self, rows_by_key: dict[str, list[dict[str, object]]]) -> None:
        self.rows_by_key = rows_by_key
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.transaction_started = False
        self.transaction_committed = False
        self.transaction_rolled_back = False
        self.closed = False

    def transaction(self) -> FakeMappingTransaction:
        return FakeMappingTransaction(self)

    async def fetch(self, query: str, *args: object):
        if 'FROM "raw_legacy".normalized_products' in query:
            return self.rows_by_key.get("normalized_products", [])
        if 'FROM "raw_legacy".tbsslipdtx' in query:
            return self.rows_by_key.get("tbsslipdtx", [])
        if 'FROM "raw_legacy".product_code_mapping_candidates' in query:
            return self.rows_by_key.get("review_candidates", [])
        if "resolution_type <> 'exact_match'" in query:
            return self.rows_by_key.get("review_mappings", [])
        if 'FROM "raw_legacy".product_code_mapping' in query:
            return self.rows_by_key.get("product_code_mapping", [])
        return []

    async def execute(self, query: str, *args: object) -> str:
        self.execute_calls.append((query, args))
        return "OK"

    async def close(self) -> None:
        self.closed = True


def test_seed_product_code_mappings_uses_verified_product_field() -> None:
    result = seed_product_code_mappings(
        rows=(
            {
                "warehouse_code": "1138",
                "product_code": "P5V-1250 OH",
                "row_count": 2,
            },
            {
                "warehouse_code": "1000",
                "product_code": "RB052-6",
                "row_count": 3,
            },
        ),
        known_product_codes={"P5V-1250 OH", "RB052"},
    )

    mapping_by_code = {mapping.legacy_code: mapping for mapping in result.mappings}

    assert mapping_by_code["P5V-1250 OH"].resolution_type == "exact_match"
    assert mapping_by_code["P5V-1250 OH"].target_code == "P5V-1250 OH"
    assert mapping_by_code["RB052-6"].target_code == UNKNOWN_PRODUCT_CODE
    assert result.orphan_code_count == 1
    assert result.orphan_row_count == 3
    assert [
        candidate.candidate_code
        for candidate in result.candidates
        if candidate.legacy_code == "RB052-6"
    ] == ["RB052"]


def test_seed_product_code_mappings_keeps_fuzzy_matches_as_review_only() -> None:
    result = seed_product_code_mappings(
        rows=(
            {"product_code": "SPZ-1900", "row_count": 4},
            {"product_code": "BMT", "row_count": 1},
        ),
        known_product_codes={"PSPZ-1900 OH", "BMT-LBC6"},
    )

    assert result.exact_match_count == 0
    assert result.unknown_count == 2
    assert result.orphan_code_count == 2
    assert result.orphan_row_count == 5
    assert all(mapping.target_code == UNKNOWN_PRODUCT_CODE for mapping in result.mappings)
    assert {candidate.legacy_code for candidate in result.candidates} == {"SPZ-1900", "BMT"}
    assert {candidate.confidence for candidate in result.candidates} == {Decimal("0.60")}


def test_corrected_orphan_baseline_constants_remain_authoritative() -> None:
    assert CORRECTED_ORPHAN_CODE_BASELINE == 190
    assert CORRECTED_ORPHAN_ROW_BASELINE == 523
    assert CORRECTED_ORPHAN_CODE_BASELINE != 660


def test_seed_product_code_mappings_ignores_blank_product_codes() -> None:
    result = seed_product_code_mappings(
        rows=(
            {"warehouse_code": "1138"},
            {"product_code": "P5V-1250 OH", "row_count": 2},
        ),
        known_product_codes={"P5V-1250 OH"},
    )

    assert result.exact_match_count == 1
    assert result.orphan_code_count == 0
    assert result.orphan_row_count == 0


@pytest.mark.asyncio
async def test_run_product_mapping_seed_is_transactional(monkeypatch) -> None:
    connection = FakeMappingConnection(
        {
            "normalized_products": [
                {"legacy_code": "P5V-1250 OH"},
                {"legacy_code": "RB052"},
            ],
            "tbsslipdtx": [
                {
                    "product_code": "P5V-1250 OH",
                    "warehouse_code": "1138",
                    "row_count": 2,
                },
                {
                    "product_code": "RB052-6",
                    "warehouse_code": "1000",
                    "row_count": 3,
                },
            ],
            "product_code_mapping": [],
        }
    )

    async def fake_open_raw_connection() -> FakeMappingConnection:
        return connection

    monkeypatch.setattr(mapping, "_open_raw_connection", fake_open_raw_connection)

    result = await mapping.run_product_mapping_seed(batch_id="batch-003")

    assert result.mapping_count == 2
    assert result.candidate_count == 1
    assert result.exact_match_count == 1
    assert result.unknown_count == 1
    assert result.orphan_code_count == 1
    assert result.orphan_row_count == 3
    assert connection.transaction_started is True
    assert connection.transaction_committed is True
    assert connection.transaction_rolled_back is False
    assert connection.closed is True
    assert any(
        'INSERT INTO "raw_legacy".normalized_products' in query
        for query, _ in connection.execute_calls
    )
    assert any(
        'INSERT INTO "raw_legacy".product_code_mapping_candidates' in query
        for query, _ in connection.execute_calls
    )
    assert any(
        'INSERT INTO "raw_legacy".product_code_mapping' in query
        for query, _ in connection.execute_calls
    )


@pytest.mark.asyncio
async def test_export_product_mapping_review_writes_csv(monkeypatch, tmp_path) -> None:
    connection = FakeMappingConnection(
        {
            "review_mappings": [
                {
                    "legacy_code": "RB052-6",
                    "target_code": "UNKNOWN",
                    "resolution_type": "unknown",
                    "confidence": Decimal("0.00"),
                    "affected_row_count": 3,
                    "review_notes": "Needs analyst review",
                }
            ],
            "review_candidates": [
                {
                    "legacy_code": "RB052-6",
                    "candidate_code": "RB052",
                    "confidence": Decimal("0.85"),
                    "heuristic": "strip-trailing-hyphen-segment",
                    "candidate_rank": 1,
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeMappingConnection:
        return connection

    monkeypatch.setattr(mapping, "_open_raw_connection", fake_open_raw_connection)

    output_path = tmp_path / "review.csv"
    result = await mapping.export_product_mapping_review(
        batch_id="batch-003",
        output_path=output_path,
    )

    assert result == ProductMappingReviewExportResult(
        batch_id="batch-003",
        schema_name="raw_legacy",
        output_path=output_path,
        exported_row_count=1,
    )
    contents = output_path.read_text(encoding="utf-8")
    assert "RB052-6" in contents
    assert "RB052" in contents


@pytest.mark.asyncio
async def test_import_product_mapping_review_applies_approved_target(monkeypatch, tmp_path) -> None:
    input_path = tmp_path / "review.csv"
    input_path.write_text(
        (
            "batch_id,legacy_code,affected_row_count,current_target_code,"
            "current_resolution_type,current_confidence,candidate_rank,"
            "candidate_code,candidate_confidence,candidate_heuristic,"
            "review_status,approved_target_code,review_notes\n"
            "batch-003,RB052-6,3,UNKNOWN,unknown,0.00,1,RB052,0.85,"
            "strip-trailing-hyphen-segment,approved,RB052,Confirmed by analyst\n"
        ),
        encoding="utf-8",
    )
    connection = FakeMappingConnection(
        {
            "normalized_products": [
                {"legacy_code": "RB052"},
                {"legacy_code": "UNKNOWN"},
            ]
        }
    )

    async def fake_open_raw_connection() -> FakeMappingConnection:
        return connection

    monkeypatch.setattr(mapping, "_open_raw_connection", fake_open_raw_connection)

    result = await mapping.import_product_mapping_review(
        batch_id="batch-003",
        input_path=input_path,
        approved_by="analyst@example.com",
    )

    assert result.applied_decision_count == 1
    upsert_calls = [
        args
        for query, args in connection.execute_calls
        if 'INSERT INTO "raw_legacy".product_code_mapping' in query
    ]
    assert upsert_calls
    assert upsert_calls[0][1] == "RB052-6"
    assert upsert_calls[0][2] == "RB052"
    assert upsert_calls[0][3] == "analyst_review"
    assert connection.transaction_started is True
    assert connection.transaction_committed is True
    assert connection.transaction_rolled_back is False
    assert any(
        'INSERT INTO "raw_legacy".normalized_products' in query
        for query, _ in connection.execute_calls
    )


@pytest.mark.asyncio
async def test_import_product_mapping_review_rejects_batch_id_mismatch(tmp_path) -> None:
    input_path = tmp_path / "review.csv"
    input_path.write_text(
        (
            "batch_id,legacy_code,affected_row_count,current_target_code,"
            "current_resolution_type,current_confidence,candidate_rank,"
            "candidate_code,candidate_confidence,candidate_heuristic,"
            "review_status,approved_target_code,review_notes\n"
            "wrong-batch,RB052-6,3,UNKNOWN,unknown,0.00,1,RB052,0.85,"
            "strip-trailing-hyphen-segment,approved,RB052,Confirmed by analyst\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="batch_id does not match requested batch"):
        await mapping.import_product_mapping_review(
            batch_id="batch-003",
            input_path=input_path,
            approved_by="analyst@example.com",
        )


@pytest.mark.asyncio
async def test_import_product_mapping_review_rejects_multiple_decisions_for_same_legacy_code(
    monkeypatch,
    tmp_path,
) -> None:
    input_path = tmp_path / "review.csv"
    input_path.write_text(
        (
            "batch_id,legacy_code,affected_row_count,current_target_code,"
            "current_resolution_type,current_confidence,candidate_rank,"
            "candidate_code,candidate_confidence,candidate_heuristic,"
            "review_status,approved_target_code,review_notes\n"
            "batch-003,RB052-6,3,UNKNOWN,unknown,0.00,1,RB052,0.85,"
            "strip-trailing-hyphen-segment,approved,RB052,First decision\n"
            "batch-003,RB052-6,3,UNKNOWN,unknown,0.00,2,RB052A,0.60,"
            "normalized-substring,keep_unknown,,Second decision\n"
        ),
        encoding="utf-8",
    )

    connection = FakeMappingConnection({"normalized_products": [{"legacy_code": "RB052"}]})

    async def fake_open_raw_connection() -> FakeMappingConnection:
        return connection

    monkeypatch.setattr(mapping, "_open_raw_connection", fake_open_raw_connection)

    with pytest.raises(ValueError, match="Multiple review decisions provided"):
        await mapping.import_product_mapping_review(
            batch_id="batch-003",
            input_path=input_path,
            approved_by="analyst@example.com",
        )

    assert connection.execute_calls == []


@pytest.mark.asyncio
async def test_import_product_mapping_review_ensures_unknown_placeholder_for_keep_unknown(
    monkeypatch,
    tmp_path,
) -> None:
    input_path = tmp_path / "review.csv"
    input_path.write_text(
        (
            "batch_id,legacy_code,affected_row_count,current_target_code,"
            "current_resolution_type,current_confidence,candidate_rank,"
            "candidate_code,candidate_confidence,candidate_heuristic,"
            "review_status,approved_target_code,review_notes\n"
            "batch-003,RB052-6,3,UNKNOWN,unknown,0.00,1,RB052,0.85,"
            "strip-trailing-hyphen-segment,keep_unknown,,Keep unresolved\n"
        ),
        encoding="utf-8",
    )
    connection = FakeMappingConnection(
        {
            "normalized_products": [],
        }
    )

    async def fake_open_raw_connection() -> FakeMappingConnection:
        return connection

    monkeypatch.setattr(mapping, "_open_raw_connection", fake_open_raw_connection)

    result = await mapping.import_product_mapping_review(
        batch_id="batch-003",
        input_path=input_path,
        approved_by="analyst@example.com",
    )

    assert result.applied_decision_count == 1
    assert any(
        'INSERT INTO "raw_legacy".normalized_products' in query
        for query, _ in connection.execute_calls
    )
    upsert_calls = [
        args
        for query, args in connection.execute_calls
        if 'INSERT INTO "raw_legacy".product_code_mapping' in query
    ]
    assert upsert_calls[0][2] == "UNKNOWN"
    assert upsert_calls[0][3] == "unknown"
