from __future__ import annotations

from scripts import propose_reconciliation_corrections as proposal_script


def test_classify_candidate_marks_category_6_as_review_only() -> None:
    disposition, reason = proposal_script.classify_candidate(
        product_code="0000",
        product_name="折讓",
        category="6",
        review_only_categories={"6"},
    )

    assert disposition == "review_only"
    assert reason == "category 6 is configured as non-merchandise review-only"


def test_classify_candidate_keeps_stock_category_actionable() -> None:
    disposition, reason = proposal_script.classify_candidate(
        product_code="PM038",
        product_name="三角皮帶 M-38",
        category="0",
        review_only_categories={"6"},
    )

    assert disposition == "actionable"
    assert reason is None