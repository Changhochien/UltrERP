"""Invoice service — create, void, and query operations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Literal, TypedDict, cast

from sqlalchemy import and_, case, func, literal, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.errors import ValidationError
from common.events import DomainEvent
from common.models.audit_log import AuditLog
from common.models.order import Order
from common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceLine
from common.models.supplier_order import SupplierOrder, SupplierOrderLine
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.customers.models import Customer
from domains.customers.validators import validate_taiwan_business_number
from domains.invoices.enums import (
    ALLOWED_EGUI_SUBMISSION_TRANSITIONS,
    BuyerType,
    EguiSubmissionStatus,
)
from domains.invoices.models import EguiSubmission, Invoice, InvoiceLine, InvoiceNumberRange
from domains.invoices.schemas import InvoiceCreate, InvoiceCreateLine
from domains.invoices.tax import aggregate_invoice_totals, calculate_line_amounts
from domains.payments.models import Payment

if TYPE_CHECKING:
    from common.object_store import ObjectStore


_B2C_SENTINEL = "0000000000"
_EGUI_LIVE_MODE = "live"
_EGUI_MOCK_MODE = "mock"


@dataclass(frozen=True)
class _UnitCostSourceRow:
    effective_date: date
    unit_cost: Decimal
    source_priority: int


@dataclass(frozen=True)
class InvoiceUnitCostBackfillPreview:
    invoice_line_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    line_number: int
    status: Literal["updated", "unmatched", "ambiguous"]
    unit_cost: Decimal | None = None


@dataclass(frozen=True)
class InvoiceUnitCostBackfillSummary:
    candidate_count: int
    updated_count: int
    skipped_count: int
    unmatched_count: int
    ambiguous_count: int
    previews: list[InvoiceUnitCostBackfillPreview]


def _format_invoice_number(prefix: str, number: int) -> str:
    return f"{prefix}{number:08d}"


def _validate_invoice_lines(lines: list[InvoiceCreateLine]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []

    if not 1 <= len(lines) <= 9999:
        errors.append(
            {
                "field": "lines",
                "message": "Invoice line count must be between 1 and 9999.",
            }
        )
        return errors

    for index, line in enumerate(lines, start=1):
        if line.quantity <= 0:
            errors.append(
                {
                    "field": f"lines[{index - 1}].quantity",
                    "message": "Quantity must be positive.",
                }
            )
        if line.unit_price < 0:
            errors.append(
                {
                    "field": f"lines[{index - 1}].unit_price",
                    "message": "Unit price must not be negative.",
                }
            )

    return errors


def normalize_buyer_identifier(
    buyer_type: BuyerType,
    buyer_identifier: str | None,
) -> str:
    if buyer_type == BuyerType.B2C:
        if buyer_identifier not in (None, ""):
            raise ValueError("B2C invoices must not provide an explicit buyer identifier.")
        return _B2C_SENTINEL

    if not buyer_identifier:
        raise ValueError("B2B invoices require a buyer identifier.")

    validation = validate_taiwan_business_number(buyer_identifier)
    if not validation.valid:
        raise ValueError("Invalid buyer identifier for B2B invoice.")

    return buyer_identifier


async def _get_customer(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> Customer | None:
    result = await session.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
        )
    )
    return cast(Customer | None, result.scalar_one_or_none())


async def _get_active_number_range(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> InvoiceNumberRange | None:
    result = await session.execute(
        select(InvoiceNumberRange)
        .where(
            InvoiceNumberRange.tenant_id == tenant_id,
            InvoiceNumberRange.is_active.is_(True),
        )
        .order_by(InvoiceNumberRange.prefix, InvoiceNumberRange.start_number)
        .limit(1)
        .with_for_update()
    )
    return cast(InvoiceNumberRange | None, result.scalar_one_or_none())


def _build_unit_cost_sources_query(
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    as_of_date: date,
):
    supplier_order_costs = (
        select(
            SupplierOrder.received_date.label("effective_date"),
            SupplierOrderLine.unit_price.label("unit_cost"),
            literal(0).label("source_priority"),
        )
        .join(SupplierOrder, SupplierOrder.id == SupplierOrderLine.order_id)
        .where(
            SupplierOrder.tenant_id == tenant_id,
            SupplierOrderLine.product_id == product_id,
            SupplierOrder.received_date.isnot(None),
            SupplierOrder.received_date <= as_of_date,
            SupplierOrderLine.unit_price.isnot(None),
        )
    )
    supplier_invoice_costs = (
        select(
            SupplierInvoice.invoice_date.label("effective_date"),
            SupplierInvoiceLine.unit_price.label("unit_cost"),
            literal(1).label("source_priority"),
        )
        .join(
            SupplierInvoice,
            SupplierInvoice.id == SupplierInvoiceLine.supplier_invoice_id,
        )
        .where(
            SupplierInvoice.tenant_id == tenant_id,
            SupplierInvoiceLine.product_id == product_id,
            SupplierInvoice.invoice_date <= as_of_date,
            SupplierInvoiceLine.unit_price.isnot(None),
        )
    )
    return supplier_order_costs.union_all(supplier_invoice_costs).subquery()


async def _fetch_ranked_unit_cost_sources(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    as_of_date: date,
) -> list[_UnitCostSourceRow]:
    cost_sources = _build_unit_cost_sources_query(
        tenant_id,
        product_id,
        as_of_date=as_of_date,
    )
    ranked_cost_sources = select(
        cost_sources.c.effective_date,
        cost_sources.c.unit_cost,
        cost_sources.c.source_priority,
        func.dense_rank()
        .over(
            order_by=(
                cost_sources.c.effective_date.desc(),
                cost_sources.c.source_priority.desc(),
            )
        )
        .label("source_rank"),
    ).subquery()
    result = await session.execute(
        select(
            ranked_cost_sources.c.effective_date,
            ranked_cost_sources.c.unit_cost,
            ranked_cost_sources.c.source_priority,
        ).where(
            ranked_cost_sources.c.source_rank == 1,
        ).order_by(
            ranked_cost_sources.c.effective_date.desc(),
            ranked_cost_sources.c.source_priority.desc(),
        )
    )
    return [
        _UnitCostSourceRow(
            effective_date=row.effective_date,
            unit_cost=row.unit_cost,
            source_priority=row.source_priority,
        )
        for row in result.all()
    ]


async def _resolve_latest_unit_cost(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    as_of_date: date,
) -> Decimal | None:
    ranked_sources = await _fetch_ranked_unit_cost_sources(
        session,
        tenant_id,
        product_id,
        as_of_date=as_of_date,
    )
    if not ranked_sources:
        return None

    winning_effective_date = ranked_sources[0].effective_date
    winning_source_priority = ranked_sources[0].source_priority
    winning_costs = {
        source.unit_cost
        for source in ranked_sources
        if source.effective_date == winning_effective_date
        and source.source_priority == winning_source_priority
    }
    if len(winning_costs) != 1:
        return None

    return next(iter(winning_costs))


def _invoice_unit_cost_backfill_decisions_cte(
    *,
    scoped_to_tenant: bool,
    seek_after_invoice_line_id: bool,
) -> str:
    tenant_filter = "AND il.tenant_id = :tenant_id" if scoped_to_tenant else ""
    seek_filter = "AND il.id > :after_invoice_line_id" if seek_after_invoice_line_id else ""
    return f"""
        WITH candidates AS (
            SELECT
                il.id AS invoice_line_id,
                il.tenant_id,
                il.product_id,
                i.invoice_number,
                i.invoice_date,
                il.line_number
            FROM invoice_lines il
            JOIN invoices i ON i.id = il.invoice_id
            WHERE il.unit_cost IS NULL
              AND il.product_id IS NOT NULL
              {tenant_filter}
                            {seek_filter}
                        ORDER BY il.id ASC
                        LIMIT :candidate_limit
        ),
        source_rows AS (
            SELECT
                c.invoice_line_id,
                src.effective_date,
                src.source_priority,
                src.unit_cost,
                DENSE_RANK() OVER (
                    PARTITION BY c.invoice_line_id
                    ORDER BY src.effective_date DESC, src.source_priority DESC
                ) AS source_rank
            FROM candidates c
            JOIN LATERAL (
                SELECT
                    so.received_date AS effective_date,
                    0 AS source_priority,
                    sol.unit_price AS unit_cost
                FROM supplier_order_line sol
                JOIN supplier_order so ON so.id = sol.order_id
                WHERE so.tenant_id = c.tenant_id
                  AND sol.product_id = c.product_id
                  AND so.received_date IS NOT NULL
                  AND so.received_date <= c.invoice_date
                  AND sol.unit_price IS NOT NULL

                UNION ALL

                SELECT
                    si.invoice_date AS effective_date,
                    1 AS source_priority,
                    sil.unit_price AS unit_cost
                FROM supplier_invoice_lines sil
                JOIN supplier_invoices si ON si.id = sil.supplier_invoice_id
                WHERE si.tenant_id = c.tenant_id
                  AND sil.product_id = c.product_id
                  AND si.invoice_date <= c.invoice_date
                  AND sil.unit_price IS NOT NULL
            ) src ON TRUE
        ),
        winning_costs AS (
            SELECT
                sr.invoice_line_id,
                COUNT(DISTINCT sr.unit_cost)
                    FILTER (WHERE sr.source_rank = 1) AS winning_cost_count,
                MIN(sr.unit_cost) FILTER (WHERE sr.source_rank = 1) AS resolved_unit_cost
            FROM source_rows sr
            GROUP BY sr.invoice_line_id
        ),
        decisions AS (
            SELECT
                c.invoice_line_id,
                c.invoice_number,
                c.invoice_date,
                c.line_number,
                CASE
                    WHEN wc.winning_cost_count IS NULL OR wc.winning_cost_count = 0 THEN 'unmatched'
                    WHEN wc.winning_cost_count = 1 THEN 'updated'
                    ELSE 'ambiguous'
                END AS status,
                wc.resolved_unit_cost AS unit_cost
            FROM candidates c
            LEFT JOIN winning_costs wc ON wc.invoice_line_id = c.invoice_line_id
        )
    """


async def backfill_missing_invoice_line_unit_costs(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None = None,
    dry_run: bool = True,
    preview_limit: int = 20,
    batch_size: int = 1000,
    max_candidates: int | None = None,
    commit_per_batch: bool = False,
) -> InvoiceUnitCostBackfillSummary:
    params_base: dict[str, object] = {}
    if tenant_id is not None:
        params_base["tenant_id"] = tenant_id

    candidate_count = 0
    updated_count = 0
    unmatched_count = 0
    ambiguous_count = 0
    previews: list[InvoiceUnitCostBackfillPreview] = []
    after_invoice_line_id: uuid.UUID | None = None
    processed_candidates = 0

    while True:
        current_batch_size = batch_size
        if max_candidates is not None:
            remaining_candidates = max_candidates - processed_candidates
            if remaining_candidates <= 0:
                break
            current_batch_size = min(current_batch_size, remaining_candidates)

        params = {
            **params_base,
            "candidate_limit": current_batch_size,
        }
        if after_invoice_line_id is not None:
            params["after_invoice_line_id"] = after_invoice_line_id

        decisions_cte = _invoice_unit_cost_backfill_decisions_cte(
            scoped_to_tenant=tenant_id is not None,
            seek_after_invoice_line_id=after_invoice_line_id is not None,
        )
        summary_result = await session.execute(
            text(
                decisions_cte
                + """
                SELECT
                    COUNT(*) AS candidate_count,
                    COUNT(*) FILTER (WHERE status = 'updated') AS updated_count,
                    COUNT(*) FILTER (WHERE status = 'unmatched') AS unmatched_count,
                    COUNT(*) FILTER (WHERE status = 'ambiguous') AS ambiguous_count,
                    MAX(invoice_line_id::text)::uuid AS last_invoice_line_id
                FROM decisions
                """
            ),
            params,
        )
        summary_row = summary_result.one()

        batch_candidate_count = int(summary_row.candidate_count or 0)
        if batch_candidate_count == 0:
            break

        batch_unmatched_count = int(summary_row.unmatched_count or 0)
        batch_ambiguous_count = int(summary_row.ambiguous_count or 0)
        batch_resolved_count = int(summary_row.updated_count or 0)
        candidate_count += batch_candidate_count
        unmatched_count += batch_unmatched_count
        ambiguous_count += batch_ambiguous_count

        remaining_preview_slots = max(preview_limit - len(previews), 0)
        if remaining_preview_slots:
            preview_result = await session.execute(
                text(
                    decisions_cte
                    + """
                    SELECT
                        invoice_line_id,
                        invoice_number,
                        invoice_date,
                        line_number,
                        status,
                        unit_cost
                    FROM decisions
                    ORDER BY invoice_line_id ASC
                    LIMIT :preview_limit
                    """
                ),
                {
                    **params,
                    "preview_limit": remaining_preview_slots,
                },
            )
            previews.extend(
                InvoiceUnitCostBackfillPreview(
                    invoice_line_id=row.invoice_line_id,
                    invoice_number=row.invoice_number,
                    invoice_date=row.invoice_date,
                    line_number=row.line_number,
                    status=row.status,
                    unit_cost=row.unit_cost,
                )
                for row in preview_result.all()
            )

        if dry_run:
            updated_count += batch_resolved_count
        elif batch_resolved_count:
            update_result = await session.execute(
                text(
                    decisions_cte
                    + """
                    UPDATE invoice_lines il
                    SET unit_cost = decisions.unit_cost
                    FROM decisions
                    WHERE decisions.status = 'updated'
                      AND il.id = decisions.invoice_line_id
                      AND il.unit_cost IS NULL
                    RETURNING il.id
                    """
                ),
                params,
            )
            updated_count += len(update_result.all())
            if commit_per_batch:
                await session.commit()

        processed_candidates += batch_candidate_count
        after_invoice_line_id = summary_row.last_invoice_line_id

    skipped_count = unmatched_count + ambiguous_count
    return InvoiceUnitCostBackfillSummary(
        candidate_count=candidate_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
        unmatched_count=unmatched_count,
        ambiguous_count=ambiguous_count,
        previews=previews,
    )


async def _create_invoice_core(
    session: AsyncSession,
    data: InvoiceCreate,
    tenant_id: uuid.UUID,
    buyer_identifier: str,
) -> Invoice:
    """Create invoice within an already-active transaction.

    Caller is responsible for session.begin() and set_tenant().
    """
    customer = await _get_customer(session, tenant_id, data.customer_id)
    if customer is None:
        raise ValidationError([{"field": "customer_id", "message": "Customer does not exist."}])

    # Validate order_id if provided
    if data.order_id is not None:
        order_check = await session.execute(
            select(Order).where(
                Order.id == data.order_id,
                Order.tenant_id == tenant_id,
            )
        )
        if order_check.scalar_one_or_none() is None:
            raise ValidationError([{"field": "order_id", "message": "Order does not exist."}])

    number_range = await _get_active_number_range(session, tenant_id)
    if number_range is None:
        raise ValidationError(
            [
                {
                    "field": "invoice_number",
                    "message": "No active invoice number range is configured.",
                }
            ]
        )

    if number_range.next_number > number_range.end_number:
        raise ValidationError(
            [
                {
                    "field": "invoice_number",
                    "message": "No invoice numbers remain in the active range.",
                }
            ]
        )

    calculated_lines = [
        calculate_line_amounts(
            quantity=line.quantity,
            unit_price=line.unit_price,
            policy_code=line.tax_policy_code,
        )
        for line in data.lines
    ]
    totals = aggregate_invoice_totals(calculated_lines)

    invoice_date = data.invoice_date or date.today()

    invoice = Invoice(
        tenant_id=tenant_id,
        invoice_number=_format_invoice_number(number_range.prefix, number_range.next_number),
        invoice_date=invoice_date,
        customer_id=customer.id,
        buyer_type=data.buyer_type.value,
        buyer_identifier_snapshot=buyer_identifier,
        currency_code=data.currency_code.upper(),
        subtotal_amount=totals["subtotal_amount"],
        tax_amount=totals["tax_amount"],
        total_amount=totals["total_amount"],
        status="issued",
        version=1,
        order_id=data.order_id,
    )

    unit_cost_cache: dict[uuid.UUID, Decimal | None] = {}
    invoice.lines = []
    for index, (line, amounts) in enumerate(
        zip(data.lines, calculated_lines, strict=True),
        start=1,
    ):
        resolved_unit_cost = line.unit_cost
        if resolved_unit_cost is None and line.product_id is not None:
            if line.product_id not in unit_cost_cache:
                unit_cost_cache[line.product_id] = await _resolve_latest_unit_cost(
                    session,
                    tenant_id,
                    line.product_id,
                    as_of_date=invoice_date,
                )
            resolved_unit_cost = unit_cost_cache[line.product_id]

        invoice.lines.append(
            InvoiceLine(
                tenant_id=tenant_id,
                line_number=index,
                product_id=line.product_id,
                product_code_snapshot=line.product_code,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                unit_cost=resolved_unit_cost,
                subtotal_amount=amounts.subtotal,
                tax_type=amounts.tax_type,
                tax_rate=amounts.tax_rate,
                tax_amount=amounts.tax_amount,
                total_amount=amounts.total_amount,
                zero_tax_rate_reason=amounts.zero_tax_rate_reason,
            )
        )

    number_range.next_number += 1
    number_range.updated_at = datetime.now(tz=UTC)

    session.add(invoice)
    await session.flush()
    return invoice


async def create_invoice_in_transaction(
    session: AsyncSession,
    data: InvoiceCreate,
    tenant_id: uuid.UUID,
    buyer_identifier: str,
) -> Invoice:
    """Create an invoice inside an already-open transaction.

    The caller owns ``session.begin()`` and tenant scoping.
    """
    if not session.in_transaction():
        raise RuntimeError(
            "create_invoice_in_transaction requires an active transaction"
        )
    return await _create_invoice_core(session, data, tenant_id, buyer_identifier)


async def create_invoice(
    session: AsyncSession,
    data: InvoiceCreate,
    tenant_id: uuid.UUID | None = None,
    *,
    artifact_store: ObjectStore | None = None,
    artifact_retention_class: str = "legal-10y",
    artifact_storage_policy: str = "standard",
    seller_ban: str = "00000000",
    seller_name: str = "UltrERP",
) -> Invoice:
    tid = tenant_id or DEFAULT_TENANT_ID

    errors = _validate_invoice_lines(data.lines)

    try:
        buyer_identifier = normalize_buyer_identifier(
            data.buyer_type,
            data.buyer_identifier,
        )
    except ValueError as exc:
        errors.append({"field": "buyer_identifier", "message": str(exc)})
        buyer_identifier = ""

    if errors:
        raise ValidationError(errors)

    async with session.begin():
        await set_tenant(session, tid)
        invoice = await create_invoice_in_transaction(
            session,
            data,
            tid,
            buyer_identifier,
        )
        if artifact_store is not None:
            from domains.invoices.artifacts import archive_invoice_xml

            await archive_invoice_xml(
                session,
                invoice,
                artifact_store,
                seller_ban=seller_ban,
                seller_name=seller_name,
                retention_class=artifact_retention_class,
                storage_policy=artifact_storage_policy,
            )

    await session.refresh(invoice)
    invoice.domain_events = [DomainEvent(name="InvoiceIssued")]
    return invoice


# ── Void window ────────────────────────────────────────────────


def compute_void_deadline(invoice_date: date) -> date:
    """Compute the Taiwan eGUI void deadline for a given invoice date.

    Filing periods are bimonthly: Jan-Feb, Mar-Apr, …, Nov-Dec.
    The void window closes on the 15th of the first month of the
    next filing period.  E.g. an invoice dated 2025-03-20 (Mar-Apr
    period) has a void deadline of 2025-05-15.
    """
    month = invoice_date.month
    # Determine end month of the bimonthly period.
    period_end_month = month + (month % 2)  # 2,4,6,8,10,12
    # Next period starts on the month after.
    next_period_start_month = period_end_month + 1
    year = invoice_date.year
    if next_period_start_month > 12:
        next_period_start_month = 1
        year += 1
    return date(year, next_period_start_month, 15)


def _normalize_egui_mode(mode: str) -> str:
    normalized = mode.lower()
    if normalized in {_EGUI_MOCK_MODE, _EGUI_LIVE_MODE}:
        return normalized
    return _EGUI_MOCK_MODE


def compute_egui_deadline(invoice: Invoice) -> datetime:
    issued_at = invoice.created_at
    if issued_at.tzinfo is None:
        issued_at = issued_at.replace(tzinfo=UTC)

    buyer_type = invoice.buyer_type.lower()
    if buyer_type == BuyerType.B2C.value:
        return issued_at + timedelta(hours=48)
    return issued_at + timedelta(days=7)


def compute_egui_deadline_label(invoice: Invoice) -> str:
    buyer_type = invoice.buyer_type.lower()
    if buyer_type == BuyerType.B2C.value:
        return "48-hour submission window"
    return "7-day submission window"


def _normalize_egui_submission_status(raw_status: str | None) -> EguiSubmissionStatus:
    try:
        return EguiSubmissionStatus(raw_status or EguiSubmissionStatus.PENDING.value)
    except ValueError:
        return EguiSubmissionStatus.PENDING


async def _select_invoice_egui_submission(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> EguiSubmission | None:
    result = await session.execute(
        select(EguiSubmission).where(
            EguiSubmission.invoice_id == invoice_id,
            EguiSubmission.tenant_id == tenant_id,
        )
    )
    return cast(EguiSubmission | None, result.scalar_one_or_none())


def serialize_invoice_egui_submission(
    submission: EguiSubmission,
    invoice: Invoice,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    current_time = now or datetime.now(tz=UTC)
    deadline_at = submission.deadline_at
    if deadline_at.tzinfo is None:
        deadline_at = deadline_at.replace(tzinfo=UTC)

    return {
        "status": submission.status,
        "mode": submission.mode,
        "fia_reference": submission.fia_reference,
        "retry_count": submission.retry_count or 0,
        "deadline_at": deadline_at,
        "deadline_label": compute_egui_deadline_label(invoice),
        "is_overdue": current_time > deadline_at,
        "last_synced_at": submission.last_synced_at,
        "last_error_message": submission.last_error_message,
        "updated_at": submission.updated_at,
    }


async def get_invoice_egui_submission(
    session: AsyncSession,
    invoice: Invoice,
    tenant_id: uuid.UUID,
    *,
    enabled: bool,
    mode: str,
    now: datetime | None = None,
) -> EguiSubmission | None:
    if not enabled:
        return None

    current_time = now or datetime.now(tz=UTC)
    submission = await _select_invoice_egui_submission(session, invoice.id, tenant_id)
    if submission is not None:
        return submission

    submission = EguiSubmission(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        status=EguiSubmissionStatus.PENDING.value,
        mode=_normalize_egui_mode(mode),
        retry_count=0,
        deadline_at=compute_egui_deadline(invoice),
        last_synced_at=current_time,
        updated_at=current_time,
    )

    # First-read detail and manual refresh can race on the same invoice.
    nested_begin = getattr(session, "begin_nested", session.begin)
    try:
        async with nested_begin():
            session.add(submission)
            await session.flush()
        return submission
    except IntegrityError as exc:
        existing_submission = await _select_invoice_egui_submission(
            session,
            invoice.id,
            tenant_id,
        )
        if existing_submission is not None:
            return existing_submission
        raise exc


def _compute_next_mock_egui_status(submission: EguiSubmission) -> EguiSubmissionStatus:
    current = _normalize_egui_submission_status(submission.status)

    if current in {EguiSubmissionStatus.ACKED, EguiSubmissionStatus.DEAD_LETTER}:
        return current
    if current == EguiSubmissionStatus.PENDING:
        return EguiSubmissionStatus.QUEUED
    if current == EguiSubmissionStatus.QUEUED:
        return EguiSubmissionStatus.SENT
    if current == EguiSubmissionStatus.SENT:
        return EguiSubmissionStatus.ACKED
    if current == EguiSubmissionStatus.FAILED:
        if submission.retry_count >= 2:
            return EguiSubmissionStatus.DEAD_LETTER
        return EguiSubmissionStatus.RETRYING
    if current == EguiSubmissionStatus.RETRYING:
        return EguiSubmissionStatus.SENT
    return current


async def refresh_invoice_egui_submission(
    session: AsyncSession,
    invoice: Invoice,
    tenant_id: uuid.UUID,
    *,
    enabled: bool,
    mode: str,
    now: datetime | None = None,
) -> EguiSubmission | None:
    submission = await get_invoice_egui_submission(
        session,
        invoice,
        tenant_id,
        enabled=enabled,
        mode=mode,
        now=now,
    )
    if submission is None:
        return None

    current_time = now or datetime.now(tz=UTC)
    submission.mode = _normalize_egui_mode(mode)
    submission.deadline_at = submission.deadline_at or compute_egui_deadline(invoice)
    submission.last_synced_at = current_time
    submission.updated_at = current_time

    if submission.mode == _EGUI_MOCK_MODE:
        current = _normalize_egui_submission_status(submission.status)
        next_status = _compute_next_mock_egui_status(submission)
        allowed = ALLOWED_EGUI_SUBMISSION_TRANSITIONS.get(current, frozenset())
        if next_status != current and next_status in allowed:
            submission.status = next_status.value
            if next_status == EguiSubmissionStatus.RETRYING:
                submission.retry_count += 1
                submission.last_error_message = "Mock FIA refresh requested a retry."
            elif next_status == EguiSubmissionStatus.ACKED:
                submission.fia_reference = (
                    submission.fia_reference or f"MOCK-{invoice.invoice_number}"
                )
                submission.last_error_message = None
            elif next_status not in {EguiSubmissionStatus.FAILED, EguiSubmissionStatus.DEAD_LETTER}:
                submission.last_error_message = None

    await session.flush()
    return submission


# ── Void invoice ───────────────────────────────────────────────


async def void_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    reason: str,
    actor_id: str = "system",
    tenant_id: uuid.UUID | None = None,
    *,
    now: datetime | None = None,
) -> Invoice:
    """Void an invoice if within the regulatory void window.

    Raises ``ValueError`` for status/window violations.
    """
    from domains.invoices.enums import ALLOWED_TRANSITIONS, InvoiceStatus

    tid = tenant_id or DEFAULT_TENANT_ID
    current_time = now or datetime.now(tz=UTC)
    today = current_time.date()

    async with session.begin():
        result = await session.execute(
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(Invoice.id == invoice_id, Invoice.tenant_id == tid)
            .with_for_update()
        )
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise ValueError("Invoice not found")

        current_status = InvoiceStatus(invoice.status)
        if InvoiceStatus.VOIDED not in ALLOWED_TRANSITIONS.get(current_status, frozenset()):
            raise ValueError(f"Cannot void invoice in status '{invoice.status}'")

        # Block void if invoice has associated payments
        paid_check = await session.execute(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0"))).where(
                Payment.invoice_id == invoice.id,
                Payment.tenant_id == tid,
                Payment.match_status == "matched",
            )
        )
        if paid_check.scalar() > 0:
            raise ValueError("Cannot void invoice with existing payments. Reverse payments first.")

        deadline = compute_void_deadline(invoice.invoice_date)
        if today > deadline:
            raise ValueError(f"Void window expired. Deadline was {deadline.isoformat()}.")

        before_state = {
            "status": invoice.status,
            "voided_at": None,
            "void_reason": None,
        }

        invoice.status = InvoiceStatus.VOIDED.value
        invoice.voided_at = current_time
        invoice.void_reason = reason
        invoice.updated_at = current_time

        after_state = {
            "status": invoice.status,
            "voided_at": invoice.voided_at.isoformat(),
            "void_reason": invoice.void_reason,
        }

        audit = AuditLog(
            tenant_id=tid,
            actor_id=actor_id,
            actor_type="user",
            action="invoice.voided",
            entity_type="invoice",
            entity_id=str(invoice.id),
            before_state=before_state,
            after_state=after_state,
            notes=reason,
        )
        session.add(audit)

        await session.flush()

    invoice.domain_events = [DomainEvent(name="InvoiceVoided")]
    return invoice


# ── Query helpers ──────────────────────────────────────────────


async def get_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> Invoice | None:
    """Fetch a single invoice with lines."""
    tid = tenant_id or DEFAULT_TENANT_ID
    result = await session.execute(
        select(Invoice)
        .options(
            selectinload(Invoice.lines),
            selectinload(Invoice.egui_submission),
        )
        .where(Invoice.id == invoice_id, Invoice.tenant_id == tid)
    )
    return result.scalar_one_or_none()


# ── Payment summary helpers ────────────────────────────────────

_DEFAULT_PAYMENT_TERMS_DAYS = 30


def _compute_due_date(
    invoice_date: date,
    payment_terms_days: int | None,
) -> date:
    days = payment_terms_days if payment_terms_days is not None else _DEFAULT_PAYMENT_TERMS_DAYS
    return invoice_date + timedelta(days=days)


def _compute_payment_status(
    invoice_status: str,
    total_amount: Decimal,
    amount_paid: Decimal,
    due_date: date,
    today: date,
) -> str:
    if invoice_status == "voided":
        return "voided"
    if invoice_status == "paid":
        return "paid"
    outstanding = total_amount - amount_paid
    if outstanding <= 0:
        return "paid"
    if today > due_date:
        return "overdue"
    if amount_paid > 0:
        return "partial"
    return "unpaid"


class PaymentSummaryDict(TypedDict):
    amount_paid: Decimal
    outstanding_balance: Decimal
    payment_status: str
    due_date: date
    days_overdue: int


async def compute_invoice_payment_summary(
    session: AsyncSession,
    invoice: Invoice,
    tenant_id: uuid.UUID,
    today: date | None = None,
) -> PaymentSummaryDict:
    """Compute payment summary for a single invoice."""
    today = today or date.today()

    # Sum matched payments
    result = await session.execute(
        select(func.coalesce(func.sum(Payment.amount), Decimal("0"))).where(
            Payment.invoice_id == invoice.id,
            Payment.tenant_id == tenant_id,
            Payment.match_status == "matched",
        )
    )
    amount_paid: Decimal = result.scalar()

    # Get payment_terms_days from linked order
    payment_terms_days: int | None = None
    if invoice.order_id is not None:
        order_result = await session.execute(
            select(Order.payment_terms_days).where(
                Order.id == invoice.order_id,
                Order.tenant_id == tenant_id,
            )
        )
        payment_terms_days = order_result.scalar_one_or_none()

    due_date = _compute_due_date(invoice.invoice_date, payment_terms_days)
    outstanding = max(Decimal("0"), invoice.total_amount - amount_paid)
    status = _compute_payment_status(
        invoice.status,
        invoice.total_amount,
        amount_paid,
        due_date,
        today,
    )
    days_overdue = max(0, (today - due_date).days) if outstanding > 0 and today > due_date else 0

    return PaymentSummaryDict(
        amount_paid=amount_paid,
        outstanding_balance=outstanding,
        payment_status=status,
        due_date=due_date,
        days_overdue=days_overdue,
    )


async def enrich_invoices_with_payment_status(
    session: AsyncSession,
    invoices: list[Invoice],
    tenant_id: uuid.UUID,
    today: date | None = None,
) -> list[dict]:
    """Batch-compute payment status for a list of invoices (avoids N+1)."""
    today = today or date.today()
    if not invoices:
        return []

    invoice_ids = [inv.id for inv in invoices]

    # Batch sum matched payments
    pay_result = await session.execute(
        select(Payment.invoice_id, func.sum(Payment.amount))
        .where(
            Payment.invoice_id.in_(invoice_ids),
            Payment.tenant_id == tenant_id,
            Payment.match_status == "matched",
        )
        .group_by(Payment.invoice_id)
    )
    paid_map: dict[uuid.UUID, Decimal] = {row[0]: row[1] for row in pay_result.all()}

    # Batch load order payment_terms_days for invoices with order_id
    order_ids = [inv.order_id for inv in invoices if inv.order_id is not None]
    terms_map: dict[uuid.UUID, int] = {}
    if order_ids:
        order_result = await session.execute(
            select(Order.id, Order.payment_terms_days).where(
                Order.id.in_(order_ids),
                Order.tenant_id == tenant_id,
            )
        )
        terms_map = {row[0]: row[1] for row in order_result.all()}

    enriched = []
    for inv in invoices:
        amount_paid = paid_map.get(inv.id, Decimal("0"))
        payment_terms = terms_map.get(inv.order_id) if inv.order_id else None
        due_date = _compute_due_date(inv.invoice_date, payment_terms)
        outstanding = max(Decimal("0"), inv.total_amount - amount_paid)
        status = _compute_payment_status(
            inv.status,
            inv.total_amount,
            amount_paid,
            due_date,
            today,
        )
        days_overdue = (
            max(0, (today - due_date).days) if outstanding > 0 and today > due_date else 0
        )

        enriched.append(
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date,
                "customer_id": inv.customer_id,
                "order_id": inv.order_id,
                "currency_code": inv.currency_code,
                "total_amount": inv.total_amount,
                "status": inv.status,
                "legacy_header_snapshot": getattr(inv, "legacy_header_snapshot", None),
                "created_at": inv.created_at,
                "amount_paid": amount_paid,
                "outstanding_balance": outstanding,
                "payment_status": status,
                "due_date": due_date,
                "days_overdue": days_overdue,
            }
        )

    return enriched


# ── Invoice list ───────────────────────────────────────────────


async def list_invoices(
    session: AsyncSession,
    tenant_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
    payment_status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[dict], int]:
    """List invoices with payment status enrichment, filtering, and sort."""
    tid = tenant_id or DEFAULT_TENANT_ID

    async with session.begin():
        await set_tenant(session, tid)

        # outstanding subquery
        paid_subq = (
            select(func.coalesce(func.sum(Payment.amount), Decimal("0")))
            .where(
                Payment.invoice_id == Invoice.id,
                Payment.tenant_id == tid,
                Payment.match_status == "matched",
            )
            .correlate(Invoice)
            .scalar_subquery()
        )
        raw_outstanding_expr = Invoice.total_amount - paid_subq
        outstanding_expr = case(
            (raw_outstanding_expr <= Decimal("0"), Decimal("0")),
            else_=raw_outstanding_expr,
        )
        non_paid_statuses = ("voided", "paid")

        base = select(Invoice).where(Invoice.tenant_id == tid)
        if customer_id:
            base = base.where(Invoice.customer_id == customer_id)
        if date_from:
            base = base.where(
                Invoice.invoice_date >= datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
            )
        if date_to:
            base = base.where(
                Invoice.invoice_date <= datetime.combine(date_to, datetime.max.time(), tzinfo=UTC)
            )
        if search:
            base = base.where(Invoice.invoice_number.ilike(f"%{search}%"))

        # outstanding subquery
        paid_subq = (
            select(func.coalesce(func.sum(Payment.amount), Decimal("0")))
            .where(
                Payment.invoice_id == Invoice.id,
                Payment.tenant_id == tid,
                Payment.match_status == "matched",
            )
            .correlate(Invoice)
            .scalar_subquery()
        )
        raw_outstanding_expr = Invoice.total_amount - paid_subq
        outstanding_expr = case(
            (raw_outstanding_expr <= Decimal("0"), Decimal("0")),
            else_=raw_outstanding_expr,
        )
        non_paid_statuses = ("voided", "paid")

        base = select(Invoice).where(Invoice.tenant_id == tid)
        if customer_id:
            base = base.where(Invoice.customer_id == customer_id)
        if date_from:
            base = base.where(
                Invoice.invoice_date >= datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
            )
        if date_to:
            base = base.where(
                Invoice.invoice_date <= datetime.combine(date_to, datetime.max.time(), tzinfo=UTC)
            )

        # Due date expression (computed in SQL to enable correct overdue pagination)
        order_terms_subq = (
            select(Order.payment_terms_days)
            .where(
                Order.id == Invoice.order_id,
                Order.tenant_id == tid,
            )
            .correlate(Invoice)
            .scalar_subquery()
        )
        due_date_expr = Invoice.invoice_date + func.coalesce(
            order_terms_subq, _DEFAULT_PAYMENT_TERMS_DAYS
        )

        # Payment status filtering — one OR'd clause per selected status
        # Must match _compute_payment_status priority: voided → paid → overdue → partial → unpaid
        if payment_status:
            statuses = [payment_status] if isinstance(payment_status, str) else list(payment_status)
            clauses = []
            for s in statuses:
                if s == "paid":
                    clauses.append(
                        and_(
                            Invoice.status != "voided",
                            or_(Invoice.status == "paid", outstanding_expr == 0),
                        )
                    )
                elif s == "unpaid":
                    clauses.append(
                        and_(
                            outstanding_expr > 0,
                            paid_subq == 0,
                            Invoice.status.notin_(non_paid_statuses),
                            due_date_expr >= func.current_date(),
                        )
                    )
                elif s == "partial":
                    clauses.append(
                        and_(
                            outstanding_expr > 0,
                            paid_subq > 0,
                            Invoice.status.notin_(non_paid_statuses),
                            due_date_expr >= func.current_date(),
                        )
                    )
                elif s == "overdue":
                    clauses.append(
                        and_(
                            outstanding_expr > 0,
                            Invoice.status.notin_(non_paid_statuses),
                            due_date_expr < func.current_date(),
                        )
                    )
            if clauses:
                base = base.where(or_(*clauses))

        # Count
        from sqlalchemy import func as sqlfunc

        count_q = select(sqlfunc.count()).select_from(base.subquery())
        total = (await session.execute(count_q)).scalar()

        # Sort
        if sort_by == "outstanding_balance":
            order_col = outstanding_expr.desc() if sort_order == "desc" else outstanding_expr.asc()
        elif sort_by == "invoice_date":
            order_col = (
                Invoice.invoice_date.desc() if sort_order == "desc" else Invoice.invoice_date.asc()
            )
        else:
            order_col = (
                Invoice.created_at.desc() if sort_order == "desc" else Invoice.created_at.asc()
            )

        result = await session.execute(
            base.order_by(order_col).offset((page - 1) * page_size).limit(page_size)
        )
        invoices = list(result.scalars().all())

        enriched = await enrich_invoices_with_payment_status(session, invoices, tid)

    return enriched, total


# ── Customer outstanding summary ──────────────────────────────


async def get_customer_outstanding(
    session: AsyncSession,
    customer_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
    today: date | None = None,
    *,
    verify_customer: bool = False,
) -> dict | None:
    """Aggregate outstanding balance across all customer invoices.

    When verify_customer=True, returns None if customer doesn't exist
    (avoids TOCTOU with a separate get_customer call).
    """
    tid = tenant_id or DEFAULT_TENANT_ID
    today = today or date.today()

    async with session.begin():
        await set_tenant(session, tid)

        if verify_customer:
            cust_check = await session.execute(
                select(Customer.id).where(
                    Customer.id == customer_id,
                    Customer.tenant_id == tid,
                )
            )
            if cust_check.scalar_one_or_none() is None:
                return None

        # Chunked iteration: process invoices in batches to avoid loading
        # all rows into memory at once. Only invoice scalars (not full
        # objects with relationships) are materialised per chunk.
        chunk_size = 1000
        last_seen_id: uuid.UUID | None = None

        outstanding_currencies: set[str] = set()
        invoice_currencies: set[str] = set()
        total_outstanding = Decimal("0")
        overdue_amount = Decimal("0")
        overdue_count = 0
        invoice_count = 0

        non_voided_filter = Invoice.tenant_id == tid
        customer_filter = Invoice.customer_id == customer_id
        status_filter = Invoice.status != "voided"

        while True:
            chunk_stmt = (
                select(
                    Invoice.id,
                    Invoice.total_amount,
                    Invoice.status,
                    Invoice.invoice_date,
                    Invoice.order_id,
                    Invoice.currency_code,
                )
                .where(non_voided_filter, customer_filter, status_filter)
                .order_by(Invoice.id)
                .limit(chunk_size)
            )
            if last_seen_id is not None:
                chunk_stmt = chunk_stmt.where(Invoice.id > last_seen_id)

            chunk_result = await session.execute(
                chunk_stmt
            )
            chunk = chunk_result.all()
            if not chunk:
                break

            normalized_chunk: list[
                tuple[
                    uuid.UUID,
                    Decimal,
                    str,
                    date,
                    uuid.UUID | None,
                    str | None,
                ]
            ] = []
            for row in chunk:
                if hasattr(row, "id"):
                    normalized_chunk.append(
                        (
                            row.id,
                            row.total_amount,
                            row.status,
                            row.invoice_date,
                            row.order_id,
                            row.currency_code,
                        )
                    )
                    continue
                normalized_chunk.append((row[0], row[1], row[2], row[3], row[4], row[5]))

            invoice_ids = [row[0] for row in normalized_chunk]

            # Batch-matched payments for this chunk only
            pay_result = await session.execute(
                select(Payment.invoice_id, func.sum(Payment.amount))
                .where(
                    Payment.invoice_id.in_(invoice_ids),
                    Payment.tenant_id == tid,
                    Payment.match_status == "matched",
                )
                .group_by(Payment.invoice_id)
            )
            paid_map: dict[uuid.UUID, Decimal] = {row[0]: row[1] for row in pay_result.all()}

            # Batch payment_terms_days for orders in this chunk
            order_ids = [row[4] for row in normalized_chunk if row[4] is not None]
            terms_map: dict[uuid.UUID, int] = {}
            if order_ids:
                terms_result = await session.execute(
                    select(Order.id, Order.payment_terms_days).where(
                        Order.id.in_(order_ids),
                        Order.tenant_id == tid,
                    )
                )
                terms_map = {row[0]: row[1] for row in terms_result.all()}

            for (
                inv_id,
                total_amount,
                status,
                invoice_date,
                order_id,
                currency_code,
            ) in normalized_chunk:
                amount_paid = paid_map.get(inv_id, Decimal("0"))
                payment_terms = terms_map.get(order_id) if order_id else None
                due_date = _compute_due_date(invoice_date, payment_terms)
                outstanding = max(Decimal("0"), total_amount - amount_paid)
                pstatus = _compute_payment_status(
                    status,
                    total_amount,
                    amount_paid,
                    due_date,
                    today,
                )

                currency = str(currency_code).upper() if currency_code else None
                if currency:
                    invoice_currencies.add(currency)

                if outstanding > 0:
                    outstanding_currencies.add(currency)
                    total_outstanding += outstanding
                    if pstatus == "overdue":
                        overdue_count += 1
                        overdue_amount += outstanding

                invoice_count += 1

            last_seen_id = normalized_chunk[-1][0]

    if len(outstanding_currencies) > 1:
        raise ValueError(
            "Customer outstanding summary is unavailable for mixed-currency receivables."
        )

    currency_code = next(iter(outstanding_currencies), None)
    if currency_code is None and len(invoice_currencies) == 1:
        currency_code = next(iter(invoice_currencies))

    return {
        "total_outstanding": total_outstanding,
        "overdue_count": overdue_count,
        "overdue_amount": overdue_amount,
        "invoice_count": invoice_count,
        "currency_code": currency_code or "TWD",
    }
