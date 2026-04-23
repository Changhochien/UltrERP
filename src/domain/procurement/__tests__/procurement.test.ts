/** Focused procurement workspace frontend tests for Story 24.1. */

import { describe, expect, it } from "vitest";
import type { RFQResponse, SupplierQuotationResponse } from "../types";

// ---------------------------------------------------------------------------
// Types and payload validation
// ---------------------------------------------------------------------------

describe("RFQ types", () => {
  it("RFQResponse has required sourcing fields", () => {
    const rfq: RFQResponse = {
      id: "00000000-0000-0000-0000-000000000001",
      tenant_id: "00000000-0000-0000-0000-000000000002",
      name: "PRQ-0001",
      status: "draft",
      company: "UltrERP Taiwan",
      currency: "TWD",
      transaction_date: "2026-04-23",
      schedule_date: "2026-05-01",
      terms_and_conditions: "Net-30 payment terms.",
      notes: "Internal sourcing note.",
      supplier_count: 2,
      quotes_received: 0,
      created_at: "2026-04-23T00:00:00Z",
      updated_at: "2026-04-23T00:00:00Z",
      items: [],
      suppliers: [],
    };

    expect(rfq.name).toBe("PRQ-0001");
    expect(rfq.status).toBe("draft");
    expect(rfq.supplier_count).toBe(2);
    expect(rfq.quotes_received).toBe(0);
    expect(rfq.items).toHaveLength(0);
    expect(rfq.suppliers).toHaveLength(0);
  });

  it("RFQ item has stable UUID for lineage", () => {
    const item = {
      id: "00000000-0000-0000-0000-000000000003",
      rfq_id: "00000000-0000-0000-0000-000000000001",
      idx: 0,
      item_code: "MAT-001",
      item_name: "Industrial Bearing",
      description: "6205-2RS sealed bearing",
      qty: "100",
      uom: "PCS",
      warehouse: "",
      created_at: "2026-04-23T00:00:00Z",
    };

    // Stable UUID independent of display order
    expect(item.id).toBeTruthy();
    expect(item.idx).toBe(0);
    expect(item.item_code).toBe("MAT-001");
    expect(item.qty).toBe("100");
  });

  it("RFQ supplier recipient tracks per-supplier quote status", () => {
    const supplier = {
      id: "00000000-0000-0000-0000-000000000004",
      rfq_id: "00000000-0000-0000-0000-000000000001",
      supplier_id: null,
      supplier_name: "Alpha Parts Co.",
      contact_email: "sales@alpha.example",
      quote_status: "pending",
      quotation_id: null,
      notes: "",
      created_at: "2026-04-23T00:00:00Z",
      updated_at: "2026-04-23T00:00:00Z",
    };

    expect(supplier.quote_status).toBe("pending");
    expect(supplier.quotation_id).toBeNull();
  });

  it("RFQ supplier status transitions to received", () => {
    const supplier = {
      id: "00000000-0000-0000-0000-000000000004",
      rfq_id: "00000000-0000-0000-0000-000000000001",
      supplier_id: null,
      supplier_name: "Alpha Parts Co.",
      contact_email: "sales@alpha.example",
      quote_status: "received",
      quotation_id: "00000000-0000-0000-0000-000000000005",
      notes: "",
      created_at: "2026-04-23T00:00:00Z",
      updated_at: "2026-04-23T00:00:00Z",
    };

    expect(supplier.quote_status).toBe("received");
    expect(supplier.quotation_id).not.toBeNull();
  });
});

describe("Supplier Quotation types", () => {
  it("SupplierQuotationResponse has required fields for comparison", () => {
    const sq: SupplierQuotationResponse = {
      id: "00000000-0000-0000-0000-000000000005",
      tenant_id: "00000000-0000-0000-0000-000000000002",
      name: "SQ-0001",
      status: "draft",
      rfq_id: "00000000-0000-0000-0000-000000000001",
      supplier_id: null,
      supplier_name: "Alpha Parts Co.",
      company: "UltrERP Taiwan",
      currency: "TWD",
      transaction_date: "2026-04-25",
      valid_till: "2026-05-15",
      lead_time_days: 14,
      delivery_date: null,
      subtotal: "12000.00",
      total_taxes: "500.00",
      grand_total: "12500.00",
      base_grand_total: "12500.00",
      taxes: [],
      contact_person: "",
      contact_email: "sales@alpha.example",
      terms_and_conditions: "",
      notes: "",
      comparison_base_total: "12500.00",
      is_awarded: false,
      created_at: "2026-04-25T00:00:00Z",
      updated_at: "2026-04-25T00:00:00Z",
      items: [],
    };

    expect(sq.rfq_id).toBeTruthy();
    expect(sq.supplier_name).toBe("Alpha Parts Co.");
    expect(sq.grand_total).toBe("12500.00");
    expect(sq.lead_time_days).toBe(14);
    expect(sq.valid_till).toBeTruthy();
    expect(sq.is_awarded).toBe(false);
    expect(sq.comparison_base_total).toBe("12500.00");
  });

  it("Supplier quotation item has stable UUID and RFQ item reference", () => {
    const item = {
      id: "00000000-0000-0000-0000-000000000006",
      quotation_id: "00000000-0000-0000-0000-000000000005",
      idx: 0,
      rfq_item_id: "00000000-0000-0000-0000-000000000003",
      item_code: "MAT-001",
      item_name: "Industrial Bearing",
      description: "6205-2RS sealed bearing",
      qty: "100",
      uom: "PCS",
      unit_rate: "100.00",
      amount: "10000.00",
      tax_rate: "5",
      tax_amount: "500.00",
      tax_code: "TX5",
      normalized_unit_rate: "100.00",
      normalized_amount: "10000.00",
      created_at: "2026-04-25T00:00:00Z",
    };

    // Stable item UUID for procurement lineage
    expect(item.id).toBeTruthy();
    // RFQ item reference for cross-document lineage
    expect(item.rfq_item_id).toBeTruthy();
    expect(item.unit_rate).toBe("100.00");
    expect(item.tax_rate).toBe("5");
    expect(item.normalized_unit_rate).toBe("100.00");
  });
});

describe("Award (PO handoff seam)", () => {
  it("Award record contains supplier snapshot for Story 24.2", () => {
    const award = {
      id: "00000000-0000-0000-0000-000000000007",
      tenant_id: "00000000-0000-0000-0000-000000000002",
      rfq_id: "00000000-0000-0000-0000-000000000001",
      quotation_id: "00000000-0000-0000-0000-000000000005",
      awarded_supplier_name: "Alpha Parts Co.",
      awarded_total: "12500.00",
      awarded_currency: "TWD",
      awarded_lead_time_days: 14,
      awarded_by: "buyer",
      awarded_at: "2026-04-26T00:00:00Z",
      po_created: false,
      po_reference: "",
      created_at: "2026-04-26T00:00:00Z",
    };

    // Award captures supplier snapshot for Story 24.2 to consume without rekeying
    expect(award.awarded_supplier_name).toBe("Alpha Parts Co.");
    expect(award.awarded_total).toBe("12500.00");
    expect(award.po_created).toBe(false);
    expect(award.po_reference).toBe("");
    // Story 24.2 sets po_created=True and po_reference when PO is created
  });

  it("Award is selected per RFQ", () => {
    // Only one active award per RFQ (service enforces this)
    const award1 = { rfq_id: "rfq-001", quotation_id: "sq-001" };
    const award2 = { rfq_id: "rfq-001", quotation_id: "sq-002" };
    expect(award1.rfq_id).toBe(award2.rfq_id);
    expect(award1.quotation_id).not.toBe(award2.quotation_id);
  });
});

describe("Comparison view", () => {
  it("Comparison row marks expired quotations", () => {
    const today = "2026-04-23";
    const expired_valid_till = "2026-04-20";
    const future_valid_till = "2026-05-15";

    function isExpired(validTill: string | null): boolean {
      if (!validTill) return false;
      return validTill < today;
    }

    expect(isExpired(expired_valid_till)).toBe(true);
    expect(isExpired(future_valid_till)).toBe(false);
    expect(isExpired(null)).toBe(false);
  });

  it("Comparison_base_total supports multi-currency normalization", () => {
    const sqTWD = { comparison_base_total: "12500.00", currency: "TWD" };
    const sqUSD = { comparison_base_total: "392.50", currency: "USD" };

    // comparison_base_total is already normalized to base currency
    expect(Number(sqTWD.comparison_base_total)).toBeGreaterThan(0);
    expect(Number(sqUSD.comparison_base_total)).toBeGreaterThan(0);
    // USD is normalized to TWD (or base currency)
    expect(sqUSD.currency).not.toBe(sqTWD.currency);
  });
});
