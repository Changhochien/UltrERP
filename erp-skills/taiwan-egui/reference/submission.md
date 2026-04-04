# eGUI Submission Workflow

## End-to-End Flow

```
Invoice Created
    │
    ▼
PENDING ─── Validation (UBN, amounts, tax) ───► Validation Failed → Fix errors
    │
    ▼ (passes validation)
QUEUED ─── Batch collector picks up invoice
    │
    ▼
XML Generation ─── MIG 4.1 C0401 format
    │
    ▼
SENT ─── Uploaded to Turnkey service
    │
    ▼
Turnkey Response
    │
    ├── Success → ACKED (invoice accepted by government)
    └── Failure → Error handling (retry or manual intervention)
```

## Validation Checks (Pre-Queue)
1. Seller UBN is valid (weighted checksum)
2. Buyer UBN is valid (for B2B invoices)
3. Invoice amounts are consistent (line totals = summary)
4. Tax calculations are correct (5% standard rate applied properly)
5. Invoice number format is valid
6. Invoice date is within current or previous filing period

## Batch Processing
- Invoices are collected in batches for submission
- Batch frequency is configurable (typically every few minutes)
- Each batch generates a submission file for the Turnkey service

## Error Handling
- Turnkey validation errors are logged and surfaced to users
- Common errors: duplicate invoice number, invalid UBN, tax mismatch
- Failed invoices can be corrected and resubmitted

## Void Submissions
- Uses C0501 document type
- Must be submitted before the void deadline (see `void-rules.md`)
- Requires the original invoice number and date

## Codebase Reference
- Submission logic is planned for a future epic
- Invoice states: `backend/domains/invoices/models.py`
