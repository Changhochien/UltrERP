## Deferred from: code review of 15-3-product-variant-mapping-workflow.md (2026-04-05)

- ~~Partial selected-table reruns in `backend/domains/legacy_import/staging.py` can drop unrelated staged tables because the current 15.1 semantics treat same-batch reruns as whole-batch replacement.~~

**RESOLVED (2026-04-07):** Fixed `run_stage_import` to only drop tables that exist in BOTH the previous run AND the current request (intersection). Tables in the previous run but not in the current partial request are now preserved. Updated test to verify non-overlapping tables are NOT dropped on partial rerun.

## Deferred from: code review of spec-24-hour-runtime-stability-hardening.md (2026-04-07)

- ~~`backend/domains/legacy_import/canonical.py` has a pre-existing dirty-worktree change in the sales and purchase line readers that appears to swap legacy source columns for `qty` and `unit_price`. This story did not introduce that mapping change, but it should be reviewed before the next legacy-import validation pass because it risks incorrect historical quantities or pricing.~~

**RESOLVED (2026-04-07):** Investigation confirmed the purchase line mapping was wrong in BOTH original and swapped versions. Real layout: col_19=unit_price, col_20=discount_multiplier, col_21=foldprice, col_22=quantity. Fixed `_fetch_purchase_lines` to use col_22 for qty and compute extended_amount = col_19×col_20×col_22. Sales line dirty-worktree changes are also verified correct: col_19=original_list_price, col_21=discounted_unit_price, col_22=line_tax_amount, col_23=qty, col_29=extended_amount, plus foldprice pre-adjustment logic (col_44/col_45). Both pipeline fixes are now verified against actual CSV data and all 72 legacy import tests pass.
## Deferred from: code review of 2-8-advanced-filter-ui.md (2026-04-13)

- **Warehouse race condition in `_get_default_warehouse_id`** [`backend/domains/orders/services.py:566`]: Two concurrent `confirm_order` calls can select the same warehouse without locking, causing double-reservation of stock. Pre-existing issue outside the scope of story 2-8.
- **No `date_from <= date_to` cross-validation** [`backend/domains/invoices/routes.py`, `backend/domains/orders/routes.py`]: If user passes `?date_from=2026-12-31&date_to=2026-01-01`, both filters apply independently yielding empty set with no error. Pre-existing gap.
- **`updated_count=0` in dry_run when batch_resolved_count=0** [`backend/domains/invoices/service.py:413`]: Conditional `if batch_resolved_count` could silently skip batches with zero candidates. Pre-existing.
