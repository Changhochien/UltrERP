"""CRM service layer - thin facade.

Implementation modules:
- _lead.py: Lead lifecycle services
- _conversion.py: Lead conversion orchestration
- _opportunity.py: Opportunity CRUD and helpers
- _quotation.py: Quotation CRUD and helpers
- _shared.py: Shared utilities
- _setup.py: CRM settings and setup
- _pipeline.py: CRM pipeline reports
"""

from __future__ import annotations

# Lead lifecycle (includes lead conversion)
from domains.crm._lead import (
    convert_lead_to_customer,
    create_lead,
    get_lead,
    handoff_lead_to_opportunity,
    list_leads,
    transition_lead_status,
    update_lead,
)

# Lead conversion orchestration
from domains.crm._conversion import convert_lead

# Opportunity
from domains.crm._opportunity import (
    _apply_opportunity_fields_to_record,
    _build_opportunity_conversion_payload,
    _build_opportunity_merged,
    _should_resolve_opportunity_party,
    create_opportunity,
    get_opportunity,
    list_opportunities,
    prepare_opportunity_quotation_handoff,
    transition_opportunity_status,
    update_opportunity,
)

# Quotation
from domains.crm._quotation import (
    _apply_quotation_fields_to_record,
    _build_quotation_conversion_payload,
    _build_quotation_merged,
    _build_quotation_record,
    _should_resolve_party,
    create_quotation,
    create_quotation_revision,
    get_quotation,
    list_quotations,
    prepare_quotation_order_handoff,
    sync_quotation_order_coverage,
    sync_quotation_order_coverage_in_transaction,
    transition_quotation_status,
    update_quotation,
)

# Shared
from domains.crm._shared import (
    _deserialize_opportunity_items,
    _deserialize_quotation_taxes,
    _line_amount_from_item,
    _resolve_party_context,
    _resolve_serialized_decimal_sum,
    _resolve_total_amount,
    _serialize_opportunity_items,
    _serialize_quotation_taxes,
    _trim,
)

# Setup
from domains.crm._setup import (
    _ensure_customer_group_supported,
    _ensure_sales_stage_supported,
    _ensure_territory_supported,
    _resolve_effective_quotation_valid_till,
    create_customer_group,
    create_sales_stage,
    create_territory,
    get_crm_settings,
    get_crm_setup_bundle,
    list_customer_groups,
    list_sales_stages,
    list_territories,
    update_crm_settings,
    update_customer_group,
    update_sales_stage,
    update_territory,
)

# Pipeline
from domains.crm._pipeline import get_crm_pipeline_report

__all__ = [
    # Lead conversion
    "convert_lead",
    "convert_lead_to_customer",
    # Lead lifecycle
    "create_lead",
    "get_lead",
    "handoff_lead_to_opportunity",
    "list_leads",
    "transition_lead_status",
    "update_lead",
    # Opportunity
    "create_opportunity",
    "get_opportunity",
    "list_opportunities",
    "prepare_opportunity_quotation_handoff",
    "transition_opportunity_status",
    "update_opportunity",
    # Quotation
    "create_quotation",
    "create_quotation_revision",
    "get_quotation",
    "list_quotations",
    "prepare_quotation_order_handoff",
    "sync_quotation_order_coverage",
    "sync_quotation_order_coverage_in_transaction",
    "transition_quotation_status",
    "update_quotation",
    # Setup
    "create_customer_group",
    "create_sales_stage",
    "create_territory",
    "get_crm_pipeline_report",
    "get_crm_settings",
    "get_crm_setup_bundle",
    "list_customer_groups",
    "list_sales_stages",
    "list_territories",
    "update_crm_settings",
    "update_customer_group",
    "update_sales_stage",
    "update_territory",
]
