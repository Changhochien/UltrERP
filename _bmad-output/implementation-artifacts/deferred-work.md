## Deferred from: code review of 15-3-product-variant-mapping-workflow.md (2026-04-05)

- ~~Partial selected-table reruns in `backend/domains/legacy_import/staging.py` can drop unrelated staged tables because the current 15.1 semantics treat same-batch reruns as whole-batch replacement.~~

**RESOLVED (2026-04-07):** Fixed `run_stage_import` to only drop tables that exist in BOTH the previous run AND the current request (intersection). Tables in the previous run but not in the current partial request are now preserved. Updated test to verify non-overlapping tables are NOT dropped on partial rerun.

## Deferred from: code review of 15-1-raw-legacy-staging-import.md (2026-04-18)

- **Date parsing loses day second digit for 8-digit all-digit dates** [backend/domains/legacy_import/normalization.py:216-217] — In `normalize_legacy_date`, for 8-digit all-digit strings (e.g. `"20240115"`), the day slice `raw[5:7]` captures only one digit. For `"20240115"`, day is parsed as `int("1")` = 1, silently dropping the `"5"`. Outside diff scope — separate normalization story concern.
- **Silent fallback swallowing ValueError with no counter/metric** [canonical.py] — The try/except wrapping of `_as_legacy_date` swallows `ValueError` and allows malformed dates to fall through silently. No counter, metric, or structured event emission for audit/data quality dashboards.
- **Holding rows have no visible drain/recovery path** [canonical.py] — `_upsert_holding_row` routes blank `doc_number` rows to holding, but no adjacent logic shows how those rows get reprocessed into the canonical flow. May be intentional design but needs explicit confirmation.
- **"tbsslipdtj" hardcoded literal is opaque** [canonical.py:1493] — Fourth argument to `_upsert_holding_row` is hardcoded as `"tbsslipdtj"`. Unclear if this is a table name, batch type, or external identifier. Pre-existing — not introduced by this diff.
- **No per-row error isolation for holding upsert** [canonical.py] — If `_upsert_holding_row` throws, the exception propagates and the `for line in lines` loop terminates. Pre-existing.
- **receipt_date→invoice_date fallback not flagged as data issue** [canonical.py] — Rows with sentinel/missing `receipt_date` are common in legacy systems and often indicate incomplete data. Warning log is insufficient for audit trails. Pre-existing.
- ~~**No test coverage changes for blank-doc_number routing**~~ — FIXED (2026-04-18): Added `test_run_canonical_import_receiving_audit_routes_blank_doc_number_to_holding` in `test_canonical.py`.
- **AC4 batch rerun idempotency not addressed by this fix** — The diff prevents UUID collisions but does not address the broader AC4 requirement that "a stage rerun alone cannot create duplicate canonical records" at the batch level. Scope question for later story.
- **AC2 lineage only captured in holding path, not main staging** — The diff adds `source_row_number` capture in the holding path. Main staging path lineage is existing code and not modified here.

## Deferred from: code review of spec-24-hour-runtime-stability-hardening.md (2026-04-07)

- ~~`backend/domains/legacy_import/canonical.py` has a pre-existing dirty-worktree change in the sales and purchase line readers that appears to swap legacy source columns for `qty` and `unit_price`. This story did not introduce that mapping change, but it should be reviewed before the next legacy-import validation pass because it risks incorrect historical quantities or pricing.~~

**RESOLVED (2026-04-07):** Investigation confirmed the purchase line mapping was wrong in BOTH original and swapped versions. Real layout: col_19=unit_price, col_20=discount_multiplier, col_21=foldprice, col_22=quantity. Fixed `_fetch_purchase_lines` to use col_22 for qty and compute extended_amount = col_19×col_20×col_22. Sales line dirty-worktree changes are also verified correct: col_19=original_list_price, col_21=discounted_unit_price, col_22=line_tax_amount, col_23=qty, col_29=extended_amount, plus foldprice pre-adjustment logic (col_44/col_45). Both pipeline fixes are now verified against actual CSV data and all 72 legacy import tests pass.
## Deferred from: code review of 2-8-advanced-filter-ui.md (2026-04-13)

- **Warehouse race condition in `_get_default_warehouse_id`** [`backend/domains/orders/services.py:566`]: Two concurrent `confirm_order` calls can select the same warehouse without locking, causing double-reservation of stock. Pre-existing issue outside the scope of story 2-8.
- **No `date_from <= date_to` cross-validation** [`backend/domains/invoices/routes.py`, `backend/domains/orders/routes.py`]: If user passes `?date_from=2026-12-31&date_to=2026-01-01`, both filters apply independently yielding empty set with no error. Pre-existing gap.
- **`updated_count=0` in dry_run when batch_resolved_count=0** [`backend/domains/invoices/service.py:413`]: Conditional `if batch_resolved_count` could silently skip batches with zero candidates. Pre-existing.

## Deferred from: code review of 19-9-prospect-gap-customer-type.md (2026-04-15)

- **Validation flags expected `excluded_path` category rows as provisional assignments** [`backend/domains/legacy_import/validation.py:291`]: `candidate_count > 0` currently raises `provisional-category-assignments` even when the only rows are expected non-merchandise `excluded_path` candidates. Pre-existing validation noise outside Story 19.9's scoped changes.

## Deferred from: code review of 1-9-backend-architecture-boundary-hardening.md (2026-04-17)

- **Stock-adjustment exceptions still surface through the pre-existing confirmation path without explicit 409 mapping** [`backend/domains/inventory/services.py:645`]: `create_stock_adjustment()` can still raise `InsufficientStockError` or `TransferValidationError` during confirmation, and that behavior predates Story 1.9.
- **Fractional order-line quantities are still truncated during reservation because confirmation continues to coerce `Decimal` quantities to `int`** [`backend/domains/inventory/order_confirmation.py:67`]: the reservation path preserves the old integer coercion behavior, so fractional quantity handling remains unresolved outside Story 1.9.

## Deferred from: code review of 12-5-print-preview-performance.md (2026-04-17)

- **Target-hardware sub-1-second proof is still a manual operator validation step rather than a recorded repo artifact** [`docs/superpowers/specs/2026-04-04-print-preview-performance.md:24`]: the runbook exists, but the repo still does not contain a recorded hardware profile plus measured durations proving the AC1 budget on target hardware.

## Deferred from: code review of 15-2-canonical-master-data-normalization.md (2026-04-18)

- **Mixed-role `tbscust` regression coverage is still missing** [`backend/tests/domains/legacy_import/test_normalization.py`]: Story 15.2 marks combined customer/supplier coverage complete, but the current suite still does not exercise a shared-party scenario that proves supplier semantics survive a customer-centric target model.

## Deferred from: code review of 15-18-automated-promotion-gate-policy-and-approved-corrections.md (2026-04-18)

- **Stale-lock recovery can unlock an active long-running refresh** [backend/scripts/legacy_refresh_state.py:16] — `recover_stale_lock()` deletes `scheduler.lock` after a fixed six-hour TTL with no heartbeat renewal, and promotion calls it before evaluation. Real issue, but the stale-lock model predates Story 15.18 and needs a broader lane-lifecycle decision.
- **Two backfill failures can leave the refresh step ledger inconsistent** [backend/scripts/run_legacy_refresh.py:660] — when both backfill coroutines fail, only the first failed step is finalized and the second can remain `running` in the persisted summary. Real issue, but it lives in the earlier Story 15.15 orchestration path.
- **Scheduled refresh publication of latest-run and latest-success is non-atomic** [backend/scripts/run_scheduled_legacy_shadow_refresh.py:344] — a write failure between the two state files can expose a newer successful `latest-run` while leaving `latest-success` stale. Real issue, but it belongs to the Story 15.16 state-publication contract.
- **Second-level scheduled batch ids can collide for rapid successive runs** [backend/scripts/run_scheduled_legacy_shadow_refresh.py:92] — `build_shadow_batch_id()` only encodes seconds, so two quick sequential invocations can reuse the same batch id. Real issue, but it predates Story 15.18 and should be addressed with the scheduler contract.
- **Promotion trusts unvalidated summary paths from latest-success state** [backend/scripts/run_legacy_promotion.py:651] — the promotion runner loads whatever `summary_path` is stored in lane state without constraining it to the approved summary root. Real issue, but the trust boundary is inherited from Story 15.17’s promotion state model.
- **Approved review imports allow whitespace-only reviewer identities** [backend/scripts/run_legacy_refresh.py:382] — `approved_by` is only checked for truthiness, so blank-but-whitespace reviewer identities pass through. Real issue, but it belongs to the pre-existing Story 15.15 review-import contract.
