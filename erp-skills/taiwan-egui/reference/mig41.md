# MIG 4.1 XML Format

## Overview
MIG (Message Implementation Guideline) 4.1 is the XML schema defined by Taiwan's Ministry of Finance for electronic invoice data exchange. UltrERP generates MIG 4.1 compliant XML for submission to the eGUI Turnkey platform.

## Document Types
- **C0401** — Invoice issuance (開立發票)
- **C0501** — Invoice void (作廢發票)
- **C0701** — Invoice allowance (折讓)

## C0401 Key Fields (Invoice Issuance)

### Main Header
| Field                | Description              | Example               |
|---------------------|--------------------------|-----------------------|
| `InvoiceNumber`     | Invoice number           | `AA-12345678`         |
| `InvoiceDate`       | Issue date (YYYYMMDD)    | `20250320`            |
| `InvoiceTime`       | Issue time (HH:MM:SS)    | `14:30:00`            |
| `SellerIdentifier`  | Seller UBN               | `04595257`            |
| `SellerName`        | Seller company name      | `台灣公司`            |
| `BuyerIdentifier`   | Buyer UBN                | `12345678`            |
| `BuyerName`         | Buyer company name       | `買方公司`            |
| `InvoiceType`       | Type code                | `07` (general B2B)    |

### Line Items (`InvoiceItem`)
| Field              | Description              |
|-------------------|--------------------------|
| `Description`     | Product/service name     |
| `Quantity`        | Quantity sold            |
| `UnitPrice`       | Unit price               |
| `Amount`          | Line subtotal            |
| `SequenceNumber`  | Line number (1-based)    |
| `TaxType`         | 1=taxable, 2=zero, 3=exempt |

### Summary (`InvoiceAmount`)
| Field              | Description              |
|-------------------|--------------------------|
| `SalesAmount`     | Total before tax         |
| `TaxType`         | Primary tax type         |
| `TaxRate`         | Rate (e.g., 0.05)       |
| `TaxAmount`       | Total tax                |
| `TotalAmount`     | Grand total with tax     |

## Encoding & Submission
- Character encoding: UTF-8
- XML declaration required
- Submitted as files to Turnkey service (see `submission.md`)

## Codebase Reference
- XML generation is planned for a future epic
- Invoice data model: `backend/domains/invoices/models.py` → `Invoice`, `InvoiceLine`
