# Taiwan eGUI Compliance Survey

## Known Facts

### MIG 4.1 (Effective January 1, 2026)
- Migration from MIG 4.0 to MIG 4.1 is mandatory as of 2026-01-01 (per SAP Help Portal confirmation and FIA announcement)
- Key MIG 4.1 changes from 4.0:
  - **CheckNumber removed** from A0101 Invoice Message (invoice check digit field deleted)
  - **CarrierId1/CarrierId2** length extended from 64 to 400 bits (supports longer carrier IDs)
  - **TaxType field added** at the line-item Details level (was summary-level only in 4.0)
  - **ZeroTaxRateReason** field added at summary level (supports zero-tax export codes 71-79)
  - **Reserved1/Reserved2** added to A0101, A0201, A0301, F0401, F0501, F0701 messages
  - **ProductItem** cardinality increased from 999 to 9999 items per invoice
  - **Description** length extended from 256 to 500 characters
  - **SequenceNumber** length extended from 3 to 4 digits
  - **Remark** (detail level) length extended from 40 to 120 characters
  - **RelateNumber** (detail level) length extended from 20 to 50 characters
  - Message types consolidated: F0401/F0501/F0701 replace the old A04xx/C04xx/A05xx/C05xx platform-certification messages

### FIA API Authentication
- Developer applies to FIA (Fiscal Information Agency, Ministry of Finance) via written or online application form
- Upon approval, FIA issues **App ID + API Key** as proof of authorized API access
- Authorization period: **maximum 3 years**; reapplication required 2-6 months before expiry
- Developer must comply with **CNS27001 or ISO27001** information security standard
- FIA Guidelines published: December 17, 2024 (version on fia.gov.tw)
- **API endpoint URL not publicly documented in freely accessible sources** -- requires FIA membership application to receive technical specs

### MIG 4.1 XML A0101 Invoice Message: Required vs. Optional Fields

**Mandatory (M) fields in Invoice/Main:**
| Field | Format | Notes |
|---|---|---|
| InvoiceNumber | 2 letters + 8 digits (e.g., QQ12345678) | Pattern: `[A-Z]{2}\d{8}` |
| InvoiceDate | YYYYMMDD | Taiwan UTC+8 timezone |
| InvoiceTime | HH:MM:SS | Taiwan UTC+8 timezone |
| Seller.Identifier | BAN, 10 chars | Seller's 統一編號 (8-digit + check digit) |
| Seller.Name | string, max 60 | Business entity name |
| Seller.RoleRemark | string, max 40 | Seller role remark |
| Buyer.Identifier | BAN, 10 chars | B2B: buyer 統一編號; B2C: 10 zeros "0000000000" |
| Buyer.Name | string, max 60 | B2B: buyer entity name; B2C: consumer identifier |
| RelateNumber | string, max 20 | (was max 50 in MIG 4.1) |
| InvoiceType | "07" or "08" | 07=general, 08=special tax rate |
| GroupMark | 1 char | Separate with "*" |
| DonateMark | "0" or "1" | 0=no donation, 1=donated |
| Details (1..9999 items) | aggregate | At least 1 ProductItem required |
| Amount/SalesAmount | decimal(20,0) | Integer, no negatives, tax excluded |
| Amount/TaxType | enum 1/2/3/4/9 | 1=taxable, 2=zero rate, 3=tax-free, 4=special rate, 9=mixed |
| Amount/TaxRate | decimal | 0.05 (=5%), 0.02 (=2%), 0.01 (=1%), 0.15 (=15%), 0.25 (=25%) |
| Amount/TaxAmount | decimal(20,0) | Integer; must match SalesAmount x TaxRate |
| Amount/TotalAmount | decimal(20,0) | Integer; must equal SalesAmount + TaxAmount |

**Optional (O) fields in Invoice/Main:**
- Seller: Address (required for seller per spec note), PersonInCharge, TelephoneNumber, FacsimileNumber, EmailAddress (max 400), CustomerNumber, RoleRemark
- Buyer: Name, Address, PersonInCharge, TelephoneNumber, FacsimileNumber, EmailAddress (max 400), CustomerNumber, RoleRemark
- BuyerRemark, MainRemark (max 200), CustomsClearanceMark, Category, GroupMark, ZeroTaxRateReason (mandatory when TaxType=2), Reserved1, Reserved2

**Mandatory fields in Invoice/Details/ProductItem (per line item):**
- Description (1-500 chars), Quantity (decimal, up to 20 digits), Unit (max 6 chars, optional), UnitPrice, **TaxType** (at detail level, MIG 4.1 new), Amount, SequenceNumber (1-4 digits)
- Optional: Remark (max 100), RelateNumber (max 50, MIG 4.1)

### Tax Rates
| TaxType | Rate | Applied To |
|---|---|---|
| 1 (taxable) | 5% | Standard general tax rate |
| 2 (zero tax rate) | 0% | Exports, international transport (codes 71-79 for zero-tax reasons) |
| 3 (tax-free) | 0% | Exempt items |
| 4 (special taxable) | 10% | Transport, insurance, machinery (special tax rates: 0.15=15%, 0.25=25%) |
| 9 (mixed) | -- | Mixture of taxable/tax-free in F0401 only |

TaxRate values: `0`, `0.01`, `0.02`, `0.05`, `0.15`, `0.25` (decimal pattern).

### Invoice State Machine
States (confirmed by context): **PENDING → QUEUED → SENT → ACKED | FAILED → RETRYING → DEAD_LETTER**
- State transitions are managed server-side by the FIA eInvoice Platform
- The API submission creates the invoice in PENDING state
- FAILED invoices enter RETRYING; after exhausting retries they go to DEAD_LETTER
- No public documentation on retry count limits or DEAD_LETTER recovery

### Submission Deadlines
- **B2C**: Invoice data must be uploaded to the tax authority within **48 hours** of issuance
- **B2B**: Within **7 days** (per multiple sources including Sovos and Voxel Group)
- **Enforcement mechanism**: The InvoiceDate/InvoiceTime in the submitted XML is the authoritative timestamp -- FIA cross-checks submission time against invoice creation time. No public documentation of how late submissions are detected/penalized. Penalty for non-compliance: fines up to TW$15,000 + late tax penalties (per Voxel Group).

### Void / Reissue Rules
- Void and reissue must be completed **by the 13th day of the first month of the next period** (ECPay documentation; e.g., invoices from January must be voided/reissued by February 13)
- This effectively means same-month void/reissue is the normal case; cross-month void is not permitted after the cutoff
- Void requires a new MIG 4.1 A0101 submission (cannot amend; must issue replacement invoice)
- InvoiceNumber cannot be reused even across years (AllownanceNumberType note)
- Failure to void/reissue correctly results in penalties under Article 48, Paragraph 1 of the Business Tax Act

### FIA API Application Process
1. Submit application to FIA (online or written form)
2. Provide supporting documents, contact information
3. Upon approval, receive App ID + API Key (authorization period: up to 3 years)
4. Reapply 2-6 months before expiration for renewal
5. Must maintain CNS27001 or ISO27001 compliance

---

## Unknowns / Open Questions

1. **FIA API endpoint URL**: No public URL was found for the production or test FIA API. The guidelines confirm App ID + API Key auth but do not publish the REST endpoint. This must be obtained from FIA after application approval.

2. **Public test/sandbox environment**: No publicly accessible FIA API sandbox was found. Approved developers appear to receive credentials for a test environment as part of the onboarding process, but there is no self-service public sandbox.

3. **48-hour enforcement mechanism**: It is unclear whether FIA detects late submissions by comparing `InvoiceDate+InvoiceTime` in the XML vs. server-received timestamp, or by some other method (e.g., "issuance time" tracked separately). This matters for PoC retry design.

4. **DEAD_LETTER recovery procedure**: The state machine includes DEAD_LETTER but no public documentation specifies: max retry attempts, retry interval, or how to recover/resubmit from DEAD_LETTER state.

5. **MIG 4.1 full schema XSD**: While MIG 4.1 changes were documented in the revision history, the complete MIG 4.1 XSD schema file was not publicly accessible as a standalone download. The MIG 4.0 PDF (dated May 30, 2024) is the most detailed public schema reference.

6. **A0102/A0301 response format**: The response message format (acknowledgement/rejection) after invoice submission was not fully extracted; specifically: what error codes are returned and how to correlate a submission ID to a state transition.

7. **Rate limits**: No public documentation of FIA API rate limits (requests/minute, concurrent connections).

8. **Void cross-month boundary**: Whether invoices issued on the last 2 days of a month have a modified void deadline (given the "by 13th of next month" rule) is ambiguous.

---

## Top 3 Risks

### 1. [HIGH] MIG 4.1 Schema Changes Not Yet in Production Systems
**Impact**: Any existing ERP integration based on MIG 4.0 will break on Jan 1, 2026 (already past). The MIG 4.1 changes are non-trivial: TaxType moved to line-item level, CheckNumber removed, SequenceNumber extended, Remark/RelateNumber lengths changed.

**Mitigation**: Obtain the MIG 4.1 XSD from FIA (upon API application) or from the einvoice.nat.gov.tw MIG 4.1 publication, and update XML serialization/deserialization before any invoice can be issued.

---

### 2. [HIGH] 48-Hour Submission Deadline -- No Grace Period Publicly Confirmed
**Impact**: B2C invoices must be submitted within 48 hours of issuance. If the FIA detects late submission (via InvoiceDate/InvoiceTime comparison), the invoice may be rejected or flagged. A failed submission enters the RETRYING → DEAD_LETTER path, potentially resulting in invoice data never reaching the authority.

**Mitigation**: Design invoice issuance + FIA submission as a tightly coupled synchronous flow. Implement a background job that polls submission status (via A0102 response) and retries FAILED submissions. Establish alerting if an invoice remains PENDING beyond 24 hours.

---

### 3. [MEDIUM] No Public Sandbox -- PoC Depends on FIA Application Timeline
**Impact**: The team cannot independently test FIA API behavior without an approved FIA developer account (App ID + API Key). The FIA application and approval process may take weeks to months, directly blocking the eGUI compliance PoC.

**Mitigation**: Initiate FIA developer registration immediately as a prerequisite PoC activity. In parallel, use the MIG 4.0/4.1 PDF schema to build XML generation and validation in isolation. Consider engaging a Taiwan eGUI-compliant third-party provider (e.g., ECPay, PChome, SHOPLINE) as a proxy integration during the waiting period.

---

## 3-Point Recommendation

1. **Initiate FIA API registration now** -- The single biggest PoC blocker is access to FIA credentials. Apply for App ID + API Key at https://www.fia.gov.tw (or via https://www.einvoice.nat.gov.tw) immediately. In parallel, obtain the official MIG 4.1 XSD from FIA or einvoice.nat.gov.tw to build schema-valid XML generation. No PoC invoice can be transmitted without approved FIA credentials.

2. **Build a MIG 4.1 XML invoice generator with full schema validation** -- Focus on the A0101 message tree. Key validation points: InvoiceNumber format `[A-Z]{2}\d{8}`, TaxType at both summary and detail level (MIG 4.1 new), all decimal precision rules (SalesAmount/TaxAmount/TotalAmount as integer decimals), ZeroTaxRateReason required when TaxType=2, DonateMark=0|1. Include a schema-validate step before any API call.

3. **Design resilient submission with state machine awareness** -- Implement the PENDING→QUEUED→SENT→ACKED|FAILED flow with explicit handling for RETRYING and DEAD_LETTER. Store the FIA-generated reference for each submission to correlate status responses. Add monitoring: if an invoice is still PENDING after 2 hours, alert and manually inspect. The 48-hour hard deadline must be enforced client-side; do not rely on FIA to notify of late submission.

---

## Sources

- FIA "Guidelines on the Use of the E-Invoice API" (published 2024-12-17): https://www.fia.gov.tw/eng/singlehtml/267?cntId=4153cda41fc646a7a99a850a0cd4dd18
- MIG 4.0 / 4.1 Message Implementation Guideline PDF (Ministry of Finance E-Invoice Platform, 2024-05-30): https://www.einvoice.nat.gov.tw/static/ptl/ein_upload/download/326.pdf
- MIG 4.1 Notice (einvoice.nat.gov.tw, Feb 2026 listing): https://www.einvoice.nat.gov.tw/ptl007w/1692781896008
- Sovos "eGUI: Taiwan's Approach to Electronic Invoicing" (2023-04-20): https://sovos.com/blog/vat/egui-taiwans-approach-to-electronic-invoicing/
- ecosio "Taiwan e-invoicing (eGUI) explained" (2026-02-27): https://ecosio.com/en/blog/taiwan-einvoicing-explained-what-businesses-need-to-know/
- EDICOM "Electronic Invoicing in Taiwan": https://edicomgroup.com/electronic-invoicing/taiwan
- Voxel Group "Electronic invoicing guide in Taiwan": https://www.voxelgroup.net/compliance/guides/taiwan/
- ECPay Developers "Invalidating and Re-issuing E-invoice": https://developers.ecpay.com.tw/22096/
- SAP Help Portal "Electronic Invoicing in Exchange Mode" (effective 2026-01-01): https://help.sap.com/docs/SAP_S4HANA_CLOUD/7fff92e3c6e244d6b6100643185233b3/e054310923c1449a9b51e2ac44630248.html
- Vertex Inc. "Taiwan (GUI): Overview": https://developer.vertexinc.com/einvoicing/docs/taiwan-overview
- VAT Update "Taiwan E-Invoicing (eGUI): Key Requirements" (2026-03-01): https://www.vatupdate.com/2026/03/01/taiwan-e-invoicing-egui-key-requirements-compliance-steps-and-penalties-for-businesses/
- Invoice Data Extraction "Taiwan E-Invoice API Integration Guide" (2026-03-11): https://invoicedataextraction.com/blog/taiwan-e-invoice-api-integration
- Sovos "Taiwan: E-Invoicing Updates Regarding e-GUI" (2024-08-23): https://sovos.com/regulatory-updates/vat/taiwan-e-invoicing-updates-regarding-e-gui/
