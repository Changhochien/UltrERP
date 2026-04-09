---
title: '24-Hour Runtime Stability Hardening'
type: 'bugfix'
created: '2026-04-07'
status: 'done'
baseline_commit: '76e8b7595151ce7165bf3cd2f0f2e720e2d2bf79'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The 24-hour runtime investigation found real stability risks in backend connection lifecycle management, legacy-import memory behavior, invoice outstanding aggregation, hot-path database indexing, FastAPI lifespan ordering, and a frontend debounced callback. Left as-is, the app can exhaust database connections, retain more memory than necessary during long-running imports and large-customer lookups, and execute callbacks after a component has unmounted.

**Approach:** Harden shared connection management first, then replace the confirmed unbounded readers with bounded or streamed access patterns, add the missing query indexes through Alembic, reorder startup/shutdown so partial initialization cannot leak resources, and patch the customer search debounce cleanup. Validate the tray overlap warning as already satisfied and do not churn that file unless a regression is discovered.

## Boundaries & Constraints

**Always:** Preserve current API contracts and import ordering; keep edits focused to the reported hot paths; preserve all unrelated uncommitted changes already in the worktree; prefer shared helper fixes over duplicating lifecycle logic at each call site; add executable validation for each touched slice where the repo already has tests or commands.

**Ask First:** Any schema change beyond the two reported indexes; any behavior change to public pagination or search response shapes; any introduction of new background workers, retry queues, or cache policies beyond shutdown cleanup.

**Never:** Revert unrelated user changes; broaden this into a general performance refactor; change the already-guarded desktop tray polling path unless validation proves the current guard is ineffective; silently weaken correctness checks for mixed-currency receivables or legacy import lineage.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| DB_ENGINE_HARDENING | App creates the shared SQLAlchemy async engine | Engine uses explicit pool sizing, timeout, recycle, and pre-ping settings suitable for long-lived workloads | Connection acquisition still fails fast with existing driver-level timeout behavior |
| RAW_IMPORT_CONNECTION_REUSE | Multiple legacy-import flows request raw asyncpg access over time | Calls share one asyncpg pool and release connections back to it instead of creating a new standalone connection each time | Pool shutdown is idempotent and does not leak connections on app shutdown |
| CUSTOMER_OUTSTANDING_LARGE_HISTORY | Customer has many non-voided invoices | Outstanding summary iterates with keyset pagination rather than OFFSET rescans, keeping bounded batch memory | Mixed-currency protection remains unchanged |
| CANONICAL_IMPORT_LARGE_BATCH | Canonical import processes large normalized and holding tables | Row access streams from asyncpg cursor support when available and falls back safely in test doubles | Import ordering and lineage behavior stay unchanged |
| FRONTEND_UNMOUNT | Customer search input unmounts while a debounce is pending | Stale timer callback does not invoke a detached `onSearch` | Timer cleanup remains idempotent |

</frozen-after-approval>

## Code Map

- `backend/common/database.py` -- shared SQLAlchemy async engine configuration for all backend DB sessions.
- `backend/domains/legacy_import/staging.py` -- raw asyncpg connection helper imported by canonical, mapping, normalization, validation, and AP payment flows.
- `backend/domains/legacy_import/canonical.py` -- canonical import readers and payment-adjacent holding logic that currently materialize large result sets.
- `backend/domains/invoices/service.py` -- customer outstanding aggregation path currently using OFFSET pagination.
- `backend/domains/inventory/services.py` -- product search relevance query and reorder alert listing hot path.
- `backend/domains/audit/queries.py` -- frequent audit-log entity filtering and newest-first sorting path that motivates the composite index.
- `backend/common/models/reorder_alert.py` -- reorder alert model definition and current index surface.
- `backend/common/models/audit_log.py` -- audit log model definition and current index surface.
- `backend/app/main.py` -- FastAPI lifespan ordering and shutdown cleanup.
- `migrations/versions/*.py` -- Alembic migration chain for adding the reported composite indexes.
- `src/components/customers/CustomerSearchBar.tsx` -- debounced search callback cleanup.

## Tasks & Acceptance

**Execution:**
- [x] `backend/common/database.py` -- add explicit async engine pool sizing, overflow, recycle, and timeout settings -- prevents long-lived deployments from relying on undersized or stale default pool behavior.
- [x] `backend/domains/legacy_import/staging.py` -- replace direct `asyncpg.connect()` usage with a shared module-level pool plus safe acquire/release helpers and shutdown cleanup -- fixes the connection-exhaustion root cause for all raw import callers.
- [x] `backend/domains/legacy_import/canonical.py` -- stream normalized and payment-adjacent reads when cursor support exists, while preserving current ordering and test-double compatibility -- reduces import-time memory spikes for large batches.
- [x] `backend/domains/invoices/service.py` -- replace OFFSET batching in `get_customer_outstanding` with keyset pagination over invoice IDs -- prevents repeated rescans and bounds aggregation memory for large customers.
- [x] `backend/domains/inventory/services.py` -- tighten `search_products` query filtering before expensive similarity ranking and keep reorder-alert behavior unchanged -- lowers search cost under broad-match queries.
- [x] `backend/app/main.py` -- move settings seeding ahead of MCP lifespan entry and close shared runtime resources on shutdown -- avoids partially initialized startup state and lingering pooled resources.
- [x] `migrations/versions/*.py` and model metadata where appropriate -- add composite indexes for reorder alerts and audit-log entity lookups -- addresses the confirmed hot-path filter/sort patterns without changing API behavior.
- [x] `src/components/customers/CustomerSearchBar.tsx` -- guard debounced `onSearch` against post-unmount invocation and add or update frontend coverage if the current test harness supports it -- removes the stale callback edge case.

**Acceptance Criteria:**
- Given the backend starts successfully, when the async engine is created, then it uses explicit pooling parameters and still exposes the same `AsyncSessionLocal` interface.
- Given any legacy-import command opens raw DB access multiple times, when each operation completes, then the connection is returned to a shared asyncpg pool and the pool can be closed during app shutdown.
- Given a customer with thousands of invoices, when outstanding totals are computed, then invoices are processed in stable keyset batches and the returned summary fields remain unchanged.
- Given large normalized or holding legacy-import tables, when canonical import reads them, then row processing can stream from the database without changing import counts, ordering, or lineage writes.
- Given a broad inventory search query, when products are searched, then the query still returns ranked results but avoids computing expensive similarity work over obviously irrelevant rows.
- Given reorder-alert and audit-log list queries run on production data, when their reported filter shapes are used, then the database has matching composite indexes available via migration.
- Given app startup or shutdown runs, when settings seeding fails or the server exits, then MCP lifespan is not left partially entered and shared caches/pools are cleaned up safely.
- Given the customer search bar unmounts with a pending debounce, when the timer would fire, then `onSearch` is not called after unmount.

## Spec Change Log

## Design Notes

The connection-pool fix should be centralized in the raw helper instead of rewritten in each legacy-import module because five separate flows already import the same function. The canonical import streaming change should prefer a helper that uses asyncpg cursor support when present and transparently falls back to `fetch()` for existing fake connections in unit tests.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/domains/payments/test_payment_status.py tests/domains/legacy_import/test_canonical.py tests/domains/inventory/test_product_search.py tests/test_aeo_sitemap.py -q` -- expected: touched backend slices stay green.
- `cd backend && uv run ruff check common app domains tests` -- expected: no new backend lint errors in touched files.
- `pnpm test -- --run src/lib/api/settings.test.ts` -- expected: frontend test harness still works after touched UI changes, and any added focused test passes.

## Suggested Review Order

**Connection Lifecycle**

- Centralizes the two 24-hour pool controls that bound backend connection churn.
	[`database.py:24`](../../backend/common/database.py#L24)

- Preserves raw asyncpg call semantics while returning connections to one shared pool.
	[`staging.py:92`](../../backend/domains/legacy_import/staging.py#L92)

- Seeds before MCP startup and closes shared runtime resources on shutdown.
	[`main.py:32`](../../backend/app/main.py#L32)

**Bounded Data Paths**

- Streams canonical-import hot reads and delays large history fetches until use.
	[`canonical.py:1764`](../../backend/domains/legacy_import/canonical.py#L1764)

- Shows the cursor-or-fetch fallback that keeps fake test connections working.
	[`canonical.py:458`](../../backend/domains/legacy_import/canonical.py#L458)

- Replaces OFFSET rescans with stable keyset batching for customer outstanding.
	[`service.py:857`](../../backend/domains/invoices/service.py#L857)

- Uses a relevance threshold instead of truncating candidates before ranking.
	[`services.py:645`](../../backend/domains/inventory/services.py#L645)

**Schema Support**

- Declares the audit-log composite index alongside the model definition.
	[`audit_log.py:19`](../../backend/common/models/audit_log.py#L19)

- Declares the reorder-alert composite index used by filter-heavy list queries.
	[`reorder_alert.py:35`](../../backend/common/models/reorder_alert.py#L35)

- Creates both new indexes concurrently to avoid blocking writes during deploy.
	[`c8d4f7a1e2b3_add_runtime_stability_indexes.py:19`](../../migrations/versions/c8d4f7a1e2b3_add_runtime_stability_indexes.py#L19)

**UI Safety And Proof**

- Cancels the debounced customer search callback after unmount.
	[`CustomerSearchBar.tsx:14`](../../src/components/customers/CustomerSearchBar.tsx#L14)

- Pins the unmount regression with a focused fake-timer test.
	[`CustomerSearchBar.test.tsx:12`](../../src/tests/customers/CustomerSearchBar.test.tsx#L12)
