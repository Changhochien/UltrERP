"""CRM lead conversion orchestration services."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import DuplicateBusinessNumberError, ValidationError
from common.tenant import DEFAULT_TENANT_ID
from domains.crm._lead import (
    _record_lead_conversion,
    _resolve_lead_status_after_conversion,
    _selected_conversion_targets,
    get_lead,
)
from domains.crm._opportunity import _build_opportunity_conversion_payload, create_opportunity
from domains.crm._quotation import _build_quotation_conversion_payload, create_quotation
from domains.crm.schemas import (
    LeadConversionRequest,
    LeadConversionResult,
    LeadConversionState,
    LeadConversionStepOutcome,
    LeadConversionStepResult,
    LeadStatus,
)
from domains.customers.service import create_customer, get_customer, lookup_customer_by_ban


# Conversion target constants for consistency across the codebase
CONVERSION_TARGET_CUSTOMER = "customer"
CONVERSION_TARGET_OPPORTUNITY = "opportunity"
CONVERSION_TARGET_QUOTATION = "quotation"


async def convert_lead(
    session: AsyncSession,
    lead_id: uuid.UUID,
    data: LeadConversionRequest,
    tenant_id: uuid.UUID | None = None,
    converted_by: str | None = None,
) -> LeadConversionResult:
    """Convert a qualified lead to customer, opportunity, and/or quotation."""
    from domains.crm.schemas import LeadQualificationStatus

    tid = tenant_id or DEFAULT_TENANT_ID
    lead = await get_lead(session, lead_id, tenant_id=tid)
    if lead is None:
        raise ValidationError([{"field": "lead_id", "message": "Lead not found."}])
    if (
        LeadQualificationStatus(lead.qualification_status)
        != LeadQualificationStatus.QUALIFIED
    ):
        raise ValidationError(
            [{"field": "qualification_status", "message": "Lead must be qualified before conversion."}]
        )

    requested_targets = _selected_conversion_targets(data)
    if not requested_targets:
        raise ValidationError(
            [{"field": "conversion", "message": "Select at least one conversion target."}]
        )

    customer_id = lead.converted_customer_id
    opportunity_id = getattr(lead, "converted_opportunity_id", None)
    quotation_id = getattr(lead, "converted_quotation_id", None)
    steps: list[LeadConversionStepResult] = []

    # Handle customer conversion
    if CONVERSION_TARGET_CUSTOMER in requested_targets:
        customer_step = await _handle_customer_conversion(
            session, data, customer_id, tid
        )
        if customer_step:
            steps.append(customer_step)
            if customer_step.outcome == LeadConversionStepOutcome.REUSED:
                customer_id = customer_step.record_id
            elif customer_step.outcome == LeadConversionStepOutcome.CREATED:
                customer_id = customer_step.record_id

    # Handle opportunity conversion
    if CONVERSION_TARGET_OPPORTUNITY in requested_targets:
        opportunity_step = await _handle_opportunity_conversion(
            session, lead, data, opportunity_id, tid
        )
        if opportunity_step:
            steps.append(opportunity_step)
            if opportunity_step.record_id:
                opportunity_id = opportunity_step.record_id

    # Handle quotation conversion
    if CONVERSION_TARGET_QUOTATION in requested_targets:
        quotation_step = await _handle_quotation_conversion(
            session, lead, data, opportunity_id, quotation_id, tid
        )
        if quotation_step:
            steps.append(quotation_step)
            if quotation_step.record_id:
                quotation_id = quotation_step.record_id

    # Record final conversion state
    successful_targets = _collect_successful_targets(steps)
    updated_lead = await _record_lead_conversion(
        session,
        lead.id,
        tenant_id=tid,
        requested_targets=requested_targets,
        converted_by=converted_by,
        customer_id=customer_id,
        opportunity_id=opportunity_id,
        quotation_id=quotation_id,
        status=_resolve_lead_status_after_conversion(successful_targets),
    )
    if updated_lead is None:
        raise ValidationError([{"field": "lead_id", "message": "Lead not found."}])

    return LeadConversionResult(
        lead_id=updated_lead.id,
        status=LeadStatus(updated_lead.status),
        conversion_state=LeadConversionState(updated_lead.conversion_state),
        conversion_path=updated_lead.conversion_path,
        converted_by=updated_lead.converted_by,
        converted_customer_id=updated_lead.converted_customer_id,
        converted_opportunity_id=updated_lead.converted_opportunity_id,
        converted_quotation_id=updated_lead.converted_quotation_id,
        converted_at=updated_lead.converted_at,
        steps=steps,
    )


async def _handle_customer_conversion(
    session: AsyncSession,
    data: LeadConversionRequest,
    existing_customer_id: uuid.UUID | None,
    tenant_id: uuid.UUID,
) -> LeadConversionStepResult | None:
    """Handle the customer conversion step."""
    if existing_customer_id is not None:
        return LeadConversionStepResult(
            target=CONVERSION_TARGET_CUSTOMER,
            outcome=LeadConversionStepOutcome.REUSED,
            record_id=existing_customer_id,
        )

    try:
        if data.reuse_customer_id is not None:
            customer = await get_customer(session, data.reuse_customer_id, tenant_id=tenant_id)
            if customer is None:
                raise ValidationError([{"field": "reuse_customer_id", "message": "Customer not found."}])
            return LeadConversionStepResult(
                target=CONVERSION_TARGET_CUSTOMER,
                outcome=LeadConversionStepOutcome.REUSED,
                record_id=customer.id,
            )

        if data.customer is not None:
            existing_customer = await lookup_customer_by_ban(
                session,
                data.customer.business_number,
                tenant_id=tenant_id,
            )
            if existing_customer is not None:
                return LeadConversionStepResult(
                    target=CONVERSION_TARGET_CUSTOMER,
                    outcome=LeadConversionStepOutcome.REUSED,
                    record_id=existing_customer.id,
                )
            created_customer = await create_customer(session, data.customer, tenant_id=tenant_id)
            return LeadConversionStepResult(
                target=CONVERSION_TARGET_CUSTOMER,
                outcome=LeadConversionStepOutcome.CREATED,
                record_id=created_customer.id,
            )

        raise ValidationError([{"field": "customer", "message": "Customer payload is required."}])

    except DuplicateBusinessNumberError as exc:
        return LeadConversionStepResult(
            target=CONVERSION_TARGET_CUSTOMER,
            outcome=LeadConversionStepOutcome.REUSED,
            record_id=exc.existing_id,
        )
    except ValidationError as exc:
        return LeadConversionStepResult(
            target=CONVERSION_TARGET_CUSTOMER,
            outcome=LeadConversionStepOutcome.FAILED,
            errors=exc.errors,
        )


async def _handle_opportunity_conversion(
    session: AsyncSession,
    lead: object,
    data: LeadConversionRequest,
    existing_opportunity_id: uuid.UUID | None,
    tenant_id: uuid.UUID,
) -> LeadConversionStepResult | None:
    """Handle the opportunity conversion step."""
    if existing_opportunity_id is not None:
        return LeadConversionStepResult(
            target=CONVERSION_TARGET_OPPORTUNITY,
            outcome=LeadConversionStepOutcome.REUSED,
            record_id=existing_opportunity_id,
        )

    try:
        if data.opportunity is None:
            raise ValidationError([{"field": "opportunity", "message": "Opportunity payload is required."}])
        opportunity = await create_opportunity(
            session,
            _build_opportunity_conversion_payload(lead, data.opportunity),
            tenant_id=tenant_id,
        )
        return LeadConversionStepResult(
            target=CONVERSION_TARGET_OPPORTUNITY,
            outcome=LeadConversionStepOutcome.CREATED,
            record_id=opportunity.id,
        )
    except ValidationError as exc:
        return LeadConversionStepResult(
            target=CONVERSION_TARGET_OPPORTUNITY,
            outcome=LeadConversionStepOutcome.FAILED,
            errors=exc.errors,
        )


async def _handle_quotation_conversion(
    session: AsyncSession,
    lead: object,
    data: LeadConversionRequest,
    opportunity_id: uuid.UUID | None,
    existing_quotation_id: uuid.UUID | None,
    tenant_id: uuid.UUID,
) -> LeadConversionStepResult | None:
    """Handle the quotation conversion step."""
    if existing_quotation_id is not None:
        return LeadConversionStepResult(
            target=CONVERSION_TARGET_QUOTATION,
            outcome=LeadConversionStepOutcome.REUSED,
            record_id=existing_quotation_id,
        )

    try:
        if data.quotation is None:
            raise ValidationError([{"field": "quotation", "message": "Quotation payload is required."}])
        quotation = await create_quotation(
            session,
            _build_quotation_conversion_payload(lead, data.quotation, opportunity_id),
            tenant_id=tenant_id,
        )
        return LeadConversionStepResult(
            target=CONVERSION_TARGET_QUOTATION,
            outcome=LeadConversionStepOutcome.CREATED,
            record_id=quotation.id,
        )
    except ValidationError as exc:
        return LeadConversionStepResult(
            target=CONVERSION_TARGET_QUOTATION,
            outcome=LeadConversionStepOutcome.FAILED,
            errors=exc.errors,
        )


def _collect_successful_targets(steps: list[LeadConversionStepResult]) -> set[str]:
    """Collect successful conversion targets from step results."""
    return {
        step.target
        for step in steps
        if step.outcome in {LeadConversionStepOutcome.CREATED, LeadConversionStepOutcome.REUSED}
    }
