# Taiwan eGUI & Tax Compliance

## Overview
Taiwan's electronic Government Uniform Invoice (eGUI / 電子發票) system is the mandatory tax reporting mechanism for B2B and B2C transactions. UltrERP generates, validates, and submits e-invoices to Taiwan's Ministry of Finance platform.

## When to Use This Skill
- Validating Unified Business Numbers (統一編號 / UBN)
- Understanding Taiwan VAT rates and tax categories
- Computing invoice void deadlines per bimonthly filing periods
- Generating MIG 4.1 XML for eGUI submission
- Troubleshooting eGUI state machine transitions

## Key Concepts
- **UBN (統一編號):** 8-digit identifier for every registered entity. Validated with weighted checksum (mod-5). See `reference/ubn-validation.md`.
- **Bimonthly Filing Periods:** Jan-Feb, Mar-Apr, May-Jun, Jul-Aug, Sep-Oct, Nov-Dec. Void deadlines fall on the 15th of the first month of the NEXT period.
- **VAT Rate:** Standard 5% on domestic sales. Zero-rated for exports. Tax-exempt for specific categories.
- **MIG 4.1:** The XML schema for e-invoice data exchange with the government platform.
- **Invoice States:** PENDING → QUEUED → SENT → ACKED

## Reference Files
- [Tax Rates](reference/tax-rates.md) — VAT rate schedule, zero-rated, exempt categories
- [UBN Validation](reference/ubn-validation.md) — Checksum algorithm with weights and special cases
- [Void Rules](reference/void-rules.md) — Bimonthly period calculation and deadline logic
- [MIG 4.1 Format](reference/mig41.md) — XML schema field mapping
- [Submission Workflow](reference/submission.md) — End-to-end eGUI submission flow
- [Invoice States](reference/states.md) — State machine transitions and error handling

## Codebase References
- UBN Validator: `backend/domains/customers/validators.py` — `validate_taiwan_business_number()`
- Void Deadline: `backend/domains/invoices/service.py` — `compute_void_deadline()`
- Invoice MCP Tools: `backend/domains/invoices/mcp.py`
