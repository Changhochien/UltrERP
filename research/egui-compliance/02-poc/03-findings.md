# MIG 4.1 + FIA API PoC Findings

**Project:** UltrERP eGUI Compliance Proof of Concept
**Date:** 2026-03-30
**Status:** PoC Complete — Full integration chain demonstrated

---

## 1. MIG 4.1 Schema Analysis

### 1.1 What Changed from MIG 4.0 to 4.1

The MIG 4.1 update (effective January 1, 2026) introduced several non-backward-compatible changes that require code updates in any existing eGUI integration:

| Change | MIG 4.0 | MIG 4.1 | Impact |
|---|---|---|---|
| **CheckNumber** | Present on A0101 Invoice/Main | **REMOVED** | Existing integrations will break if they still output this field |
| **TaxType** | Summary-level only | **Added at line-item Details level** | Every ProductItem now requires a TaxType element |
| **CarrierId1/CarrierId2** | 64-bit max | Extended to **400 bits** | Supports new carrier ID formats |
| **ZeroTaxRateReason** | Not present | **Added at summary Amount level** | Required when TaxType=2 (zero-rate exports) |
| **ProductItem cardinality** | max 999 | **max 9999** | Supports larger invoices |
| **Description length** | 256 chars | **500 chars** | More room for product descriptions |
| **SequenceNumber length** | 3 digits | **4 digits** | Extends sequence range |
| **Remark (detail) length** | 40 chars | **120 chars** | More detail remarks |
| **RelateNumber (detail) length** | 20 chars | **50 chars** | More cross-reference room |
| **Reserved1/Reserved2** | Not present | **Added to A0101, A0201, A0301, F0401, F0501, F0701** | Future extensibility |

### 1.2 Required Fields for A0101 Invoice Submission

**Mandatory (M) fields in Invoice/Main:**

```
InvoiceNumber      — 2 uppercase letters + 8 digits  (e.g., QQ12345678)
InvoiceDate        — YYYYMMDD in Taiwan UTC+8
InvoiceTime        — HH:MM:SS in Taiwan UTC+8
Seller.Identifier  — 統一編號 (9-char BAN: 8 digits + check digit)
Seller.Name        — Business entity name (max 60 chars)
Seller.RoleRemark  — Seller role remark (max 40 chars)
Buyer.Identifier   — B2B: buyer BAN; B2C: 0000000000
Buyer.Name         — B2B: entity name; B2C: consumer identifier
RelateNumber       — Internal order reference (max 20 chars)
InvoiceType        — "07" (general) or "08" (special tax rate)
GroupMark          — "0" or separate with "*"
DonateMark         — "0" (no) or "1" (yes)
Details/ProductItem — At least 1 item required
Amount/SalesAmount — Integer decimal(20,0), tax excluded
Amount/TaxType     — 1|2|3|4|9 (summary level; per-item also required in 4.1)
Amount/TaxRate     — 0|0.01|0.02|0.05|0.15|0.25
Amount/TaxAmount   — Integer; must equal SalesAmount × TaxRate
Amount/TotalAmount — Integer; must equal SalesAmount + TaxAmount
```

**Mandatory at line-item (ProductItem) level (MIG 4.1 new):**

```
Description    — 1 to 500 characters
Quantity       — Decimal, up to 20 digits
UnitPrice      — Decimal
Amount         — Decimal (line-level total)
SequenceNumber — 1 to 4 digits (MIG 4.1 extended from 3)
TaxType        — Enum 1|2|3|4|9 (MIG 4.1 new at detail level)
```

**Conditionally mandatory:**

```
Amount/ZeroTaxRateReason — Required when TaxType=2 (zero-rate exports, codes 71-79)
```

### 1.3 Tax Rate Mapping

| TaxType | Rate | Applied To | Notes |
|---|---|---|---|
| 1 (taxable) | 5% (0.05) | Standard general tax | Most common |
| 2 (zero-rate) | 0% | Exports, international transport | Requires ZeroTaxRateReason |
| 3 (tax-free) | 0% | Exempt items | No ZeroTaxRateReason needed |
| 4 (special) | 10% (0.15, 0.25) | Transport, insurance, machinery | |
| 9 (mixed) | — | F0401 only | Mixture of taxable/tax-free |

### 1.4 BAN (Business Association Number) Validation

The 9-character 統一編號 (8 digits + check digit) uses a mod-10 weighting algorithm. Validation steps:

1. First 8 digits multiplied by `[1, 2, 1, 2, 1, 2, 1, 2]` from left
2. Sum all resulting digits (tens digit + units digit for products > 9)
3. Compute: `(10 - (sum mod 10)) mod 10`
4. Result must equal the 9th digit (check digit)

This check is enforced by both `mig41_generator.py` and `fia_mock_server.py`.

---

## 2. FIA API Mock Behavior

### 2.1 Simulated Endpoints

The mock server (`fia_mock_server.py`) implements three endpoints on `localhost:8080`:

| Endpoint | Method | Behavior |
|---|---|---|
| `/api/invoice/submit` | POST | Accepts A0101 XML, returns ACK or REJECT |
| `/api/invoice/status/<ref>` | GET | Returns current state of a submission |
| `/health` | GET | Returns server health status |

### 2.2 Submit Endpoint Response Types

**ACK (HTTP 200, status=ACCEPTED):** Returned when:
- XML is well-formed and parses successfully
- All required MIG 4.1 fields are present and non-empty
- Seller BAN passes check-digit validation
- InvoiceDate is within the 48-hour window (mock: always passes)
- Returns a `reference_number` (format: `MIG41-{12-char-HEX}`) and initial state `PENDING`

**REJECT (HTTP 400, status=REJECTED):** Returned when:
- XML is malformed (parse error)
- Missing required MIG 4.1 fields (Main/InvoiceNumber, Seller/Identifier, Details, Amount, etc.)
- Seller BAN check digit is invalid
- InvoiceDate violates 48-hour window (not mocked — always passes)

### 2.3 State Machine Simulation

The mock server runs a background thread that advances invoices through the state machine:

```
PENDING
  └─(0.5s)→ QUEUED
              └─(1.5s)→ SENT
                         ├─(2.5s)→ ACKED  (80% chance)
                         └─(2.5s)→ FAILED (20% chance — simulates transmission error)
                                    │
                              (auto-retry up to 3x)
                                    │
                         ┌─(3s+delay)→ RETRYING
                         │                 │
                         │            (70% succeed → SENT)
                         │            (30% fail → FAILED or DEAD_LETTER if max retries)
                         └─(max 3 retries)→ DEAD_LETTER
```

The 20% first-attempt failure rate is intentional to demonstrate retry logic without requiring a real FIA connection.

### 2.4 Mock Limitations (vs. Real FIA)

| Aspect | Mock | Real FIA |
|---|---|---|
| Authentication | None | App ID + API Key required |
| Endpoint URL | localhost:8080 | Provided after FIA application approval |
| Sandbox | Self-contained | Requires approved developer account |
| 48-hour enforcement | Bypassed (always passes) | InvoiceDate+InvoiceTime vs. server timestamp comparison |
| DEAD_LETTER recovery | N/A | Procedure not publicly documented |
| Rate limits | None | Unknown (no public documentation) |
| Retry intervals | Fixed 1.5-5s | Unknown — server-side |

---

## 3. State Machine Implementation Notes

### 3.1 State Definitions

| State | Meaning |
|---|---|
| **PENDING** | Invoice received, queued for processing |
| **QUEUED** | Queued for transmission to tax authority |
| **SENT** | Transmitted to FIA platform |
| **ACKED** | Confirmed by FIA — invoice is registered |
| **FAILED** | Transmission failed; will be retried automatically |
| **RETRYING** | Retry in progress |
| **DEAD_LETTER** | All retries exhausted; manual intervention required |

### 3.2 Client-Side Retry Design

The `submit_invoice.py` client implements the following retry logic:

1. Submit XML → receive ACK with reference number and initial state
2. Poll `/api/invoice/status/<ref>` every 1 second (up to 30 attempts)
3. On `FAILED` state: re-submit the same invoice (up to 3 retries configured)
4. On `ACKED`: success — exit with code 0
5. On `DEAD_LETTER`: failure — exit with code 1, print action required
6. On poll exhaustion: warning — last known state logged

### 3.3 48-Hour Window

The 48-hour window is calculated from `InvoiceDate + InvoiceTime` in the submitted XML versus the server's receive timestamp. In the PoC mock, this check is bypassed (always returns True). In production, late submissions beyond 48 hours will be rejected with `SUBMISSION_LATE` error code.

**Key design implication:** Invoice issuance and FIA submission must be tightly coupled in the real system. The 48-hour deadline must be enforced client-side; the FIA does not send notifications for approaching deadlines.

### 3.4 Same-Month Void/Reissue Rule

Void and reissue must be completed **by the 13th day of the first month of the next period** (e.g., January invoices must be voided/reissued by February 13). This means:
- Same-month void/reissue is the normal case
- Cross-month void is not permitted after the cutoff
- Void requires a new MIG 4.1 A0101 submission (no in-place amendment)
- Failure to void correctly results in Article 48 penalties

---

## 4. Recommendations for Real FIA Integration

### 4.1 Immediate Actions

1. **Initiate FIA API registration now** — The single biggest PoC blocker is access to FIA credentials. Apply at `https://www.fia.gov.tw` or via `https://www.einvoice.nat.gov.tw`. The approval process may take weeks to months and is required before any real invoice can be transmitted.

2. **Obtain the official MIG 4.1 XSD** — The complete schema file should be requested from FIA or downloaded from `einvoice.nat.gov.tw` upon registration. The PoC generator is based on the MIG 4.1 revision notes but a production integration must use the authoritative XSD for schema validation.

3. **Build schema-valid XML before any API call** — Every invoice XML must pass full MIG 4.1 schema validation (XSD or equivalent) before being submitted. FIA will REJECT invalid XML; repeated rejections may trigger rate limiting or account review.

### 4.2 Architecture Recommendations

**Tightly couple invoice issuance + FIA submission:**
```
Invoice Created → [Validate MIG 4.1] → [Submit to FIA] → [Poll for ACK]
                                      → [Store ref + state]
                                      → [Alert if PENDING > 24h]
```

**Implement resilient submission with state awareness:**
- Store FIA `reference_number` in your invoice record
- Poll submission state asynchronously after initial ACK
- Implement a background retry job for FAILED invoices
- Alert if invoice remains PENDING beyond 2 hours
- Design for DEAD_LETTER manual intervention workflow

**Enforce 48-hour deadline client-side:**
- Calculate remaining time on every invoice after issuance
- If > 40 hours since issuance with no ACK, escalate immediately
- Do not rely on FIA to notify of late submission — they reject silently

### 4.3 Invoice Number Management

Invoice numbers follow the format `AA12345678` (2 letters + 8 digits). These:
- Must be unique (cannot be reused even across years)
- Cannot be amended after submission — void and reissue instead
- Must use a new InvoiceNumber for each retry (in production)

### 4.4 Third-Party Proxy Option

While waiting for FIA approval, consider using a Taiwan eGUI-compliant third-party provider as a proxy integration:
- **ECPay** — well-documented eInvoice API
- **PChome** — eGUI-compliant services
- **SHOPLINE** — built-in eGUI compliance for merchants

These providers handle FIA submission on your behalf and can be used as an interim solution while awaiting direct FIA API access.

---

## 5. PoC File Inventory

| File | Purpose |
|---|---|
| `mig41_generator.py` | Generates MIG 4.1 A0101 compliant XML with validation |
| `fia_mock_server.py` | Mock FIA API server with state machine simulation |
| `submit_invoice.py` | Client that submits XML and tracks state transitions |
| `sample_invoice.xml` | Generated by `mig41_generator.py` — valid MIG 4.1 invoice |
| `03-findings.md` | This document |

### Run Instructions

```bash
# Terminal 1: Generate the sample invoice XML
python mig41_generator.py

# Terminal 2: Start the mock FIA server
python fia_mock_server.py

# Terminal 3: Submit the invoice (from the 02-poc directory)
python submit_invoice.py

# To test REJECT behavior with invalid XML:
python submit_invoice.py --xml <invalid_file.xml>
```
