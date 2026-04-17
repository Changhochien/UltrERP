from __future__ import annotations

from decimal import Decimal

import pytest

from domains.legacy_import import category_review
from domains.legacy_import.category_review import (
    ProductCategoryReviewExportResult,
    ProductCategoryReviewImportResult,
)


class FakeCategoryReviewTransaction:
    def __init__(self, connection: "FakeCategoryReviewConnection") -> None:
        self.connection = connection

    async def __aenter__(self) -> "FakeCategoryReviewTransaction":
        self.connection.transaction_started = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            self.connection.transaction_committed = True
        else:
            self.connection.transaction_rolled_back = True
        return False


class FakeCategoryReviewConnection:
    def __init__(self, rows_by_key: dict[str, list[dict[str, object]]]) -> None:
        self.rows_by_key = rows_by_key
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.transaction_started = False
        self.transaction_committed = False
        self.transaction_rolled_back = False
        self.closed = False

    def transaction(self) -> FakeCategoryReviewTransaction:
        return FakeCategoryReviewTransaction(self)

    async def fetch(self, query: str, *args: object):
        if 'FROM "raw_legacy".product_category_review_candidates' in query:
            return self.rows_by_key.get("review_candidates", [])
        return []

    async def execute(self, query: str, *args: object) -> str:
        self.execute_calls.append((query, args))
        return "OK"

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_export_product_category_review_writes_csv(monkeypatch, tmp_path) -> None:
    connection = FakeCategoryReviewConnection(
        {
            "review_candidates": [
                {
                    "legacy_code": "SHIP01",
                    "name": "郵寄運費",
                    "legacy_category": "Misc",
                    "stock_kind": "6",
                    "current_category": "Non-Merchandise",
                    "category_source": "exclusion_rule",
                    "category_rule_id": "stock-kind-non-merchandise",
                    "category_confidence": Decimal("1.00"),
                    "review_reason": "excluded_path",
                }
            ]
        }
    )

    async def fake_open_raw_connection() -> FakeCategoryReviewConnection:
        return connection

    monkeypatch.setattr(category_review, "_open_raw_connection", fake_open_raw_connection)

    output_path = tmp_path / "category-review.csv"
    result = await category_review.export_product_category_review(
        batch_id="batch-003",
        output_path=output_path,
    )

    assert result == ProductCategoryReviewExportResult(
        batch_id="batch-003",
        schema_name="raw_legacy",
        output_path=output_path,
        exported_row_count=1,
    )
    contents = output_path.read_text(encoding="utf-8")
    assert "SHIP01" in contents
    assert "excluded_path" in contents
    assert "Non-Merchandise" in contents


@pytest.mark.asyncio
async def test_import_product_category_review_upserts_override(monkeypatch, tmp_path) -> None:
    input_path = tmp_path / "category-review.csv"
    input_path.write_text(
        (
            "batch_id,legacy_code,name,legacy_category,stock_kind,current_category,"
            "category_source,category_rule_id,category_confidence,review_reason,"
            "review_status,approved_category,review_notes\n"
            "batch-003,SHIP01,郵寄運費,Misc,6,Non-Merchandise,exclusion_rule,"
            "stock-kind-non-merchandise,1.00,excluded_path,approved,Other Power Transmission,"
            "Treat as reviewed exception\n"
        ),
        encoding="utf-8",
    )
    connection = FakeCategoryReviewConnection(
        {
            "review_candidates": [
                {
                    "legacy_code": "SHIP01",
                }
            ]
        }
    )
    refreshed_batches: list[tuple[str, object, str]] = []

    async def fake_open_raw_connection() -> FakeCategoryReviewConnection:
        return connection

    async def fake_refresh_review_batch(*, batch_id: str, tenant_id, schema_name: str) -> None:
        refreshed_batches.append((batch_id, tenant_id, schema_name))

    monkeypatch.setattr(category_review, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(category_review, "_refresh_review_batch", fake_refresh_review_batch)

    result = await category_review.import_product_category_review(
        batch_id="batch-003",
        input_path=input_path,
        approved_by="analyst@example.com",
    )

    assert result == ProductCategoryReviewImportResult(
        batch_id="batch-003",
        schema_name="raw_legacy",
        input_path=input_path,
        applied_decision_count=1,
    )
    upsert_calls = [
        args
        for query, args in connection.execute_calls
        if 'INSERT INTO "raw_legacy".product_category_override' in query
    ]
    assert upsert_calls
    assert upsert_calls[0][1] == "SHIP01"
    assert upsert_calls[0][2] == "Other Power Transmission"
    assert upsert_calls[0][4] == "review-import"
    assert upsert_calls[0][5] == "analyst@example.com"
    assert connection.transaction_started is True
    assert connection.transaction_committed is True
    assert connection.transaction_rolled_back is False
    assert refreshed_batches == [("batch-003", category_review.DEFAULT_TENANT_ID, "raw_legacy")]


@pytest.mark.asyncio
async def test_import_product_category_review_rejects_unknown_status(tmp_path) -> None:
    input_path = tmp_path / "category-review.csv"
    input_path.write_text(
        (
            "batch_id,legacy_code,name,legacy_category,stock_kind,current_category,"
            "category_source,category_rule_id,category_confidence,review_reason,"
            "review_status,approved_category,review_notes\n"
            "batch-003,SHIP01,郵寄運費,Misc,6,Non-Merchandise,exclusion_rule,"
            "stock-kind-non-merchandise,1.00,excluded_path,skip,,Treat as reviewed exception\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported review_status"):
        await category_review.import_product_category_review(
            batch_id="batch-003",
            input_path=input_path,
            approved_by="analyst@example.com",
        )


@pytest.mark.asyncio
async def test_import_product_category_review_rejects_keep_current_with_changed_category(
    tmp_path,
) -> None:
    input_path = tmp_path / "category-review.csv"
    input_path.write_text(
        (
            "batch_id,legacy_code,name,legacy_category,stock_kind,current_category,"
            "category_source,category_rule_id,category_confidence,review_reason,"
            "review_status,approved_category,review_notes\n"
            "batch-003,SHIP01,郵寄運費,Misc,6,Non-Merchandise,exclusion_rule,"
            "stock-kind-non-merchandise,1.00,excluded_path,keep_current,Other Power Transmission,"
            "Treat as reviewed exception\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="keep_current cannot change category"):
        await category_review.import_product_category_review(
            batch_id="batch-003",
            input_path=input_path,
            approved_by="analyst@example.com",
        )


@pytest.mark.asyncio
async def test_import_product_category_review_rejects_unknown_review_candidate(
    monkeypatch,
    tmp_path,
) -> None:
    input_path = tmp_path / "category-review.csv"
    input_path.write_text(
        (
            "batch_id,legacy_code,name,legacy_category,stock_kind,current_category,"
            "category_source,category_rule_id,category_confidence,review_reason,"
            "review_status,approved_category,review_notes\n"
            "batch-003,UNKNOWN01,郵寄運費,Misc,6,Non-Merchandise,exclusion_rule,"
            "stock-kind-non-merchandise,1.00,excluded_path,approved,Other Power Transmission,"
            "Treat as reviewed exception\n"
        ),
        encoding="utf-8",
    )
    connection = FakeCategoryReviewConnection(
        {
            "review_candidates": [
                {
                    "legacy_code": "SHIP01",
                }
            ]
        }
    )

    async def fake_open_raw_connection() -> FakeCategoryReviewConnection:
        return connection

    monkeypatch.setattr(category_review, "_open_raw_connection", fake_open_raw_connection)

    with pytest.raises(ValueError, match="Unknown review candidate"):
        await category_review.import_product_category_review(
            batch_id="batch-003",
            input_path=input_path,
            approved_by="analyst@example.com",
        )