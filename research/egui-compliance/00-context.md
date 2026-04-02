# eGUI Compliance Context

Source: /Volumes/2T_SSD_App/Projects/UltrERP/design-artifacts/A-Product-Brief/2026-03-30-erp-architecture-design.md

Taiwan eGUI requirements:
- MIG 4.1 standard (effective January 1, 2026, update from 4.0)
- FIA API submission within 48 hours of invoice creation
- Tax rates: 5% (standard), 10% (transport/insurance/machinery), 0% (exempt exports)
- State machine: PENDING→QUEUED→SENT→ACKED|FAILED→RETRYING→DEAD_LETTER
- Void/reissue: same month only, requires new MIG 4.1 submission

Invoice data required for MIG 4.1 XML:
- 統一編號 (tax ID, 8 digits + check digit)
- 發票日期 (invoice date)
- 品項明細 (line items: description, quantity, unit price, tax)
- 稅額 (tax amount)

Key research questions:
- FIA API endpoint URLs and authentication (App ID + API Key)
- Rate limits and submissionretry logic
- MIG 4.1 XML schema (required vs optional fields)
- 48-hour enforcement: how does FIA detect late submissions?
- Void same-month: can you void and reissue in same month?
