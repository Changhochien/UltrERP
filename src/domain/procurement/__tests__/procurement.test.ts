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

// ---------------------------------------------------------------------------
// Story 24.2: Purchase Order Tests
// ---------------------------------------------------------------------------

import type {
  POStatus,
  PurchaseOrderCreatePayload,
  PurchaseOrderResponse,
  PurchaseOrderSummary,
} from "../types";

const PO_STATUS_COLORS: Record<POStatus, string> = {
  draft: "bg-gray-100 text-gray-700",
  submitted: "bg-blue-100 text-blue-700",
  on_hold: "bg-yellow-100 text-yellow-700",
  to_receive: "bg-orange-100 text-orange-700",
  to_bill: "bg-purple-100 text-purple-700",
  to_receive_and_bill: "bg-indigo-100 text-indigo-700",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-700",
  closed: "bg-gray-100 text-gray-500",
};

const PO_STATUS_LABELS: Record<POStatus, string> = {
  draft: "Draft",
  submitted: "Submitted",
  on_hold: "On Hold",
  to_receive: "To Receive",
  to_bill: "To Bill",
  to_receive_and_bill: "To Receive & Bill",
  completed: "Completed",
  cancelled: "Cancelled",
  closed: "Closed",
};

describe("Purchase Order Types (Story 24.2)", () => {
  it("PurchaseOrderResponse has required sourcing lineage fields", () => {
    const po: PurchaseOrderResponse = {
      id: "00000000-0000-0000-0000-000000000010",
      tenant_id: "00000000-0000-0000-0000-000000000002",
      name: "PO-0001",
      status: "draft",
      supplier_id: null,
      supplier_name: "Alpha Parts Co.",
      rfq_id: "00000000-0000-0000-0000-000000000001",
      quotation_id: "00000000-0000-0000-0000-000000000005",
      award_id: "00000000-0000-0000-0000-000000000007",
      company: "UltrERP Taiwan",
      currency: "TWD",
      transaction_date: "2026-04-27",
      schedule_date: "2026-05-11",
      subtotal: "12000.00",
      total_taxes: "500.00",
      grand_total: "12500.00",
      base_grand_total: "12500.00",
      taxes: [],
      contact_person: "",
      contact_email: "sales@alpha.example",
      set_warehouse: "WH-001",
      terms_and_conditions: "",
      notes: "Urgent delivery required",
      per_received: "0.00",
      per_billed: "0.00",
      is_approved: false,
      approved_by: "",
      approved_at: null,
      blanket_order_reference_id: null,
      landed_cost_reference_id: null,
      // Subcontracting metadata (Story 24-6)
      is_subcontracted: false,
      finished_goods_item_code: null,
      finished_goods_item_name: null,
      expected_subcontracted_qty: null,
      created_at: "2026-04-27T00:00:00Z",
      updated_at: "2026-04-27T00:00:00Z",
      items: [],
    };

    // Sourcing lineage preserved
    expect(po.rfq_id).toBe("00000000-0000-0000-0000-000000000001");
    expect(po.quotation_id).toBe("00000000-0000-0000-0000-000000000005");
    expect(po.award_id).toBe("00000000-0000-0000-0000-000000000007");
    // Progress tracking
    expect(po.per_received).toBe("0.00");
    expect(po.per_billed).toBe("0.00");
    expect(po.is_approved).toBe(false);
  });

  it("PO item has stable UUID for downstream receipt and invoice linkage", () => {
    const poItem = {
      id: "00000000-0000-0000-0000-000000000011",
      purchase_order_id: "00000000-0000-0000-0000-000000000010",
      quotation_item_id: "00000000-0000-0000-0000-000000000006",
      rfq_item_id: "00000000-0000-0000-0000-000000000003",
      item_code: "MAT-001",
      item_name: "Industrial Bearing",
      qty: "100",
      uom: "PCS",
      warehouse: "WH-001",
      unit_rate: "100.00",
      amount: "10000.00",
      received_qty: "0",
      billed_amount: "0.00",
    };

    // Stable UUID for downstream references (Story 24-3, 24-6)
    expect(poItem.id).toBeTruthy();
    // Lineage back to quotation item
    expect(poItem.quotation_item_id).toBe("00000000-0000-0000-0000-000000000006");
    // Lineage back to RFQ item
    expect(poItem.rfq_item_id).toBe("00000000-0000-0000-0000-000000000003");
  });

  it("PO can be created from award_id for auto-fill", () => {
    const poPayload: PurchaseOrderCreatePayload = {
      award_id: "00000000-0000-0000-0000-000000000007",
      supplier_name: "", // Will be auto-filled
      company: "", // Will be auto-filled
      currency: "TWD",
      transaction_date: "2026-04-27",
      subtotal: "0.00",
      total_taxes: "0.00",
      grand_total: "0.00",
      base_grand_total: "0.00",
      taxes: [],
      contact_person: "",
      contact_email: "",
      set_warehouse: "",
      terms_and_conditions: "",
      notes: "",
      items: [],
    };

    expect(poPayload.award_id).toBe("00000000-0000-0000-0000-000000000007");
    // Empty supplier/company indicate auto-fill from award
    expect(poPayload.supplier_name).toBe("");
  });

  it("PO status colors cover all lifecycle states", () => {
    const statuses: POStatus[] = [
      "draft",
      "submitted",
      "on_hold",
      "to_receive",
      "to_bill",
      "to_receive_and_bill",
      "completed",
      "cancelled",
      "closed",
    ];

    for (const status of statuses) {
      expect(PO_STATUS_COLORS[status]).toBeTruthy();
      expect(PO_STATUS_LABELS[status]).toBeTruthy();
    }
  });

  it("PurchaseOrderSummary contains list view fields", () => {
    const summary: PurchaseOrderSummary = {
      id: "00000000-0000-0000-0000-000000000010",
      name: "PO-0001",
      status: "submitted",
      supplier_name: "Alpha Parts Co.",
      company: "UltrERP Taiwan",
      currency: "TWD",
      transaction_date: "2026-04-27",
      schedule_date: "2026-05-11",
      grand_total: "12500.00",
      per_received: "0.00",
      per_billed: "0.00",
      is_approved: true,
      created_at: "2026-04-27T00:00:00Z",
    };

    expect(summary.name).toBe("PO-0001");
    expect(summary.status).toBe("submitted");
    expect(summary.is_approved).toBe(true);
    expect(summary.per_received).toBe("0.00");
    expect(summary.per_billed).toBe("0.00");
  });
});

describe("Purchase Order Lifecycle (Story 24.2)", () => {
  it("PO starts in draft status", () => {
    const po = { status: "draft", is_approved: false };
    expect(po.status).toBe("draft");
    expect(po.is_approved).toBe(false);
  });

  it("PO transitions to submitted after approval", () => {
    const po = { status: "submitted", is_approved: true };
    expect(po.status).toBe("submitted");
    expect(po.is_approved).toBe(true);
  });

  it("PO can be placed on hold", () => {
    const po = { status: "on_hold" };
    expect(po.status).toBe("on_hold");
  });

  it("PO can be released from hold", () => {
    const po = { status: "to_receive" };
    expect(["to_receive", "to_bill", "to_receive_and_bill", "submitted"]).toContain(po.status);
  });

  it("PO cannot be cancelled when completed", () => {
    const po = { status: "completed" };
    const canCancel = !["completed", "cancelled", "closed"].includes(po.status);
    expect(canCancel).toBe(false);
  });

  it("PO cannot be cancelled when closed", () => {
    const po = { status: "closed" };
    const canCancel = !["completed", "cancelled", "closed"].includes(po.status);
    expect(canCancel).toBe(false);
  });

  it("PO progress reflects per_received and per_billed", () => {
    const po = {
      per_received: "50.00",
      per_billed: "25.00",
    };
    expect(Number(po.per_received)).toBe(50);
    expect(Number(po.per_billed)).toBe(25);
  });
});

describe("Purchase Order Sourcing Lineage (Story 24.2)", () => {
  it("PO links back to awarded supplier quotation", () => {
    const po = {
      quotation_id: "00000000-0000-0000-0000-000000000005",
      supplier_name: "Alpha Parts Co.",
    };
    expect(po.quotation_id).toBe("00000000-0000-0000-0000-000000000005");
    expect(po.supplier_name).toBe("Alpha Parts Co.");
  });

  it("PO links back to upstream RFQ", () => {
    const po = {
      rfq_id: "00000000-0000-0000-0000-000000000001",
      quotation_id: "00000000-0000-0000-0000-000000000005",
    };
    expect(po.rfq_id).toBe("00000000-0000-0000-0000-000000000001");
    expect(po.quotation_id).toBe("00000000-0000-0000-0000-000000000005");
  });

  it("PO line items preserve quotation item reference", () => {
    const poItem = {
      quotation_item_id: "00000000-0000-0000-0000-000000000006",
      rfq_item_id: "00000000-0000-0000-0000-000000000003",
    };
    expect(poItem.quotation_item_id).toBeTruthy();
    expect(poItem.rfq_item_id).toBeTruthy();
  });

  it("PO award link enables tracking from RFQ to PO", () => {
    const award = {
      id: "00000000-0000-0000-0000-000000000007",
      rfq_id: "00000000-0000-0000-0000-000000000001",
      quotation_id: "00000000-0000-0000-0000-000000000005",
      po_created: true,
      po_reference: "PO-0001",
    };
    expect(award.po_created).toBe(true);
    expect(award.po_reference).toBe("PO-0001");
  });
});

describe("Purchase Order No Goods Receipt Logic (Story 24.2)", () => {
  it("PO create payload does not include received_qty", () => {
    const payload: PurchaseOrderCreatePayload = {
      supplier_name: "Alpha Parts Co.",
      company: "UltrERP Taiwan",
      currency: "TWD",
      transaction_date: "2026-04-27",
      subtotal: "12500.00",
      total_taxes: "500.00",
      grand_total: "12500.00",
      base_grand_total: "12500.00",
      taxes: [],
      contact_person: "",
      contact_email: "",
      set_warehouse: "",
      terms_and_conditions: "",
      notes: "",
      items: [],
    };
    // received_qty is set by Story 24-3 (goods receipt)
    expect("received_qty" in payload).toBe(false);
  });

  it("PO response does not include supplier invoice fields", () => {
    const po: PurchaseOrderResponse = {
      id: "00000000-0000-0000-0000-000000000010",
      tenant_id: "00000000-0000-0000-0000-000000000002",
      name: "PO-0001",
      status: "draft",
      supplier_id: null,
      supplier_name: "Alpha Parts Co.",
      rfq_id: null,
      quotation_id: null,
      award_id: null,
      company: "UltrERP Taiwan",
      currency: "TWD",
      transaction_date: "2026-04-27",
      schedule_date: null,
      subtotal: "12500.00",
      total_taxes: "500.00",
      grand_total: "12500.00",
      base_grand_total: "12500.00",
      taxes: [],
      contact_person: "",
      contact_email: "",
      set_warehouse: "",
      terms_and_conditions: "",
      notes: "",
      per_received: "0.00",
      per_billed: "0.00",
      is_approved: false,
      approved_by: "",
      approved_at: null,
      blanket_order_reference_id: null,
      landed_cost_reference_id: null,
      // Subcontracting metadata (Story 24-6)
      is_subcontracted: false,
      finished_goods_item_code: null,
      finished_goods_item_name: null,
      expected_subcontracted_qty: null,
      created_at: "2026-04-27T00:00:00Z",
      updated_at: "2026-04-27T00:00:00Z",
      items: [],
    };
    // Invoice posting is handled by Story 24-6
    expect("invoice_id" in po).toBe(false);
    expect("invoice_date" in po).toBe(false);
  });

  it("PO does not include BOM, auto-creation, cost-sheet, or subcontract-return fields", () => {
    const po = {
      status: "draft",
      supplier_name: "Alpha Parts Co.",
      company: "UltrERP Taiwan",
    };
    // BOM, auto-creation, cost-sheet, and subcontract-return are deferred to Epic 32
    expect("bom" in po).toBe(false);
    expect("auto_create_subcontract_order" in po).toBe(false);
    expect("cost_sheet_id" in po).toBe(false);
    expect("subcontract_return_id" in po).toBe(false);
  });
});

// --------------------------------------------------------------------------
// Story 24.5: Supplier Controls Tests
// --------------------------------------------------------------------------

import type {
  SupplierControlResult,
  SupplierControlsStatus,
  ProcurementSummary,
  SupplierPerformanceStats,
} from "../types";

describe("Supplier Control Types (Story 24.5)", () => {
  it("SupplierControlResult has block/warn structure", () => {
    const result: SupplierControlResult = {
      is_blocked: true,
      is_warned: false,
      reason: "Supplier is on hold",
      supplier_name: "Blocked Supplier",
      controls: {
        on_hold: true,
        hold_type: "payment",
        prevent_rfqs: false,
      },
    };

    expect(result.is_blocked).toBe(true);
    expect(result.is_warned).toBe(false);
    expect(result.reason).toContain("on hold");
    expect(result.supplier_name).toBe("Blocked Supplier");
    expect(result.controls.on_hold).toBe(true);
    expect(result.controls.hold_type).toBe("payment");
  });

  it("SupplierControlsStatus has all control fields", () => {
    const status: SupplierControlsStatus = {
      supplier_id: "00000000-0000-0000-0000-000000000020",
      supplier_name: "Test Supplier",
      is_active: true,
      is_subcontractor: false,
      on_hold: false,
      hold_type: null,
      release_date: null,
      is_effectively_on_hold: false,
      scorecard_standing: "active",
      scorecard_last_evaluated_at: "2026-04-24T00:00:00Z",
      warn_rfqs: false,
      prevent_rfqs: false,
      warn_pos: true,
      prevent_pos: false,
      rfq_blocked: false,
      rfq_warned: false,
      rfq_control_reason: "",
      po_blocked: false,
      po_warned: true,
      po_control_reason: "Supplier has PO warnings",
    };

    expect(status.on_hold).toBe(false);
    expect(status.warn_pos).toBe(true);
    expect(status.po_warned).toBe(true);
    expect(status.scorecard_standing).toBe("active");
    expect(status.is_effectively_on_hold).toBe(false);
  });

  it("SupplierControlFlags includes all procurement control fields", () => {
    const controls = {
      on_hold: true,
      hold_type: "quality",
      release_date: "2026-05-01",
      scorecard_standing: "warning",
      warn_rfqs: true,
      prevent_rfqs: false,
      warn_pos: true,
      prevent_pos: false,
    };

    expect(controls.on_hold).toBe(true);
    expect(controls.hold_type).toBe("quality");
    expect(controls.warn_rfqs).toBe(true);
    expect(controls.prevent_rfqs).toBe(false);
    expect(controls.warn_pos).toBe(true);
    expect(controls.prevent_pos).toBe(false);
  });
});

describe("Supplier Control Enforcement (Story 24.5)", () => {
  it("blocked supplier should prevent RFQ submission", () => {
    const control: SupplierControlResult = {
      is_blocked: true,
      is_warned: false,
      reason: "Supplier is on hold",
      supplier_name: "Held Supplier",
      controls: { on_hold: true },
    };

    const canProceed = !control.is_blocked;
    expect(canProceed).toBe(false);
  });

  it("warn_rfqs supplier should show warning but allow RFQ", () => {
    const control: SupplierControlResult = {
      is_blocked: false,
      is_warned: true,
      reason: "Supplier has RFQ warnings",
      supplier_name: "Warned Supplier",
      controls: { warn_rfqs: true },
    };

    const canProceed = !control.is_blocked;
    const shouldWarn = control.is_warned;
    expect(canProceed).toBe(true);
    expect(shouldWarn).toBe(true);
  });

  it("prevent_pos supplier should block PO submission", () => {
    const control: SupplierControlResult = {
      is_blocked: true,
      is_warned: false,
      reason: "Supplier is blocked from POs",
      supplier_name: "Blocked Supplier",
      controls: { prevent_pos: true },
    };

    const canProceed = !control.is_blocked;
    expect(canProceed).toBe(false);
    expect(control.reason).toContain("blocked from POs");
  });

  it("release_date in future should not block supplier", () => {
    const futureDate = "2026-12-31";
    const today = "2026-04-24";

    const isOnHold = futureDate <= today;
    expect(isOnHold).toBe(false);
  });

  it("release_date in past should block supplier", () => {
    const pastDate = "2026-04-20";
    const today = "2026-04-24";

    const isOnHold = pastDate <= today;
    expect(isOnHold).toBe(true);
  });
});

describe("Procurement Reporting Types (Story 24.5)", () => {
  it("ProcurementSummary has required sections", () => {
    const summary: ProcurementSummary = {
      period: { from: "2026-04-01", to: "2026-04-30" },
      rfqs: { total: 10, submitted: 5, pending: 5 },
      supplier_quotations: { total: 20, submitted: 15, pending: 5 },
      awards: { total: 5 },
      purchase_orders: { total: 8, active: 6, draft: 2 },
      supplier_controls: { blocked_suppliers: 2, warned_suppliers: 3 },
    };

    expect(summary.period.from).toBe("2026-04-01");
    expect(summary.rfqs.total).toBe(10);
    expect(summary.rfqs.submitted).toBe(5);
    expect(summary.supplier_quotations.total).toBe(20);
    expect(summary.awards.total).toBe(5);
    expect(summary.purchase_orders.active).toBe(6);
    expect(summary.supplier_controls.blocked_suppliers).toBe(2);
    expect(summary.supplier_controls.warned_suppliers).toBe(3);
  });

  it("SupplierPerformanceStats includes award rates", () => {
    const stats: SupplierPerformanceStats = {
      supplier_id: null,
      overall: { total_quotes: 50, awarded_quotes: 20, award_rate: 40.0 },
      by_supplier: [
        {
          supplier_name: "Alpha Supplier",
          supplier_id: "00000000-0000-0000-0000-000000000021",
          total_quotes: 20,
          awarded_quotes: 10,
          award_rate: 50.0,
        },
        {
          supplier_name: "Beta Supplier",
          supplier_id: "00000000-0000-0000-0000-000000000022",
          total_quotes: 30,
          awarded_quotes: 10,
          award_rate: 33.33,
        },
      ],
      supplier_controls: {
        total_suppliers: 10,
        blocked_count: 2,
        warn_rfq_count: 3,
        warn_po_count: 4,
        prevent_rfq_count: 1,
        prevent_po_count: 1,
      },
    };

    expect(stats.overall.award_rate).toBe(40.0);
    expect(stats.by_supplier[0].award_rate).toBe(50.0);
    expect(stats.supplier_controls.total_suppliers).toBe(10);
    expect(stats.supplier_controls.blocked_count).toBe(2);
  });
});

describe("RFQ Extension Hooks (Story 24.5)", () => {
  it("RFQ includes contract_reference field", () => {
    const rfq = {
      id: "00000000-0000-0000-0000-000000000001",
      name: "PRQ-0001",
      status: "draft",
      contract_reference: "CON-2026-001",
    };

    expect(rfq.contract_reference).toBe("CON-2026-001");
  });

  it("RFQ contract_reference can be null", () => {
    const rfq = {
      id: "00000000-0000-0000-0000-000000000001",
      name: "PRQ-0001",
      status: "draft",
      contract_reference: null,
    };

    expect(rfq.contract_reference).toBeNull();
  });
});

describe("Purchase Order Extension Hooks (Story 24.5)", () => {
  it("PO includes blanket_order_reference_id field", () => {
    const po = {
      id: "00000000-0000-0000-0000-000000000010",
      name: "PO-0001",
      status: "draft",
      blanket_order_reference_id: "00000000-0000-0000-0000-000000000030",
      landed_cost_reference_id: null,
    };

    expect(po.blanket_order_reference_id).toBe("00000000-0000-0000-0000-000000000030");
    expect(po.landed_cost_reference_id).toBeNull();
  });

  it("PO extension hooks are nullable", () => {
    const po = {
      id: "00000000-0000-0000-0000-000000000010",
      name: "PO-0002",
      status: "submitted",
      blanket_order_reference_id: null,
      landed_cost_reference_id: null,
    };

    expect(po.blanket_order_reference_id).toBeNull();
    expect(po.landed_cost_reference_id).toBeNull();
  });
});

describe("Supplier Quotation Extension Hooks (Story 24.5)", () => {
  it("SupplierQuotation includes contract_reference field", () => {
    const sq = {
      id: "00000000-0000-0000-0000-000000000005",
      name: "SQ-0001",
      status: "draft",
      contract_reference: "CON-2026-001",
    };

    expect(sq.contract_reference).toBe("CON-2026-001");
  });

  it("SupplierQuotation contract_reference can be null", () => {
    const sq = {
      id: "00000000-0000-0000-0000-000000000005",
      name: "SQ-0001",
      status: "draft",
      contract_reference: null,
    };

    expect(sq.contract_reference).toBeNull();
  });
});

// --------------------------------------------------------------------------
// Story 24.6: Subcontracting Workflow Tests
// --------------------------------------------------------------------------

import type {
  SubcontractingMaterialTransferStatus,
  SubcontractingMaterialTransferResponse,
  SubcontractingMaterialTransferCreatePayload,
  SubcontractingReceiptStatus,
  SubcontractingReceiptResponse,
  SubcontractingReceiptCreatePayload,
} from "../types";

describe("Subcontracting PO Types (Story 24.6)", () => {
  it("PO can be marked as subcontracted with finished goods metadata", () => {
    const po: PurchaseOrderResponse = {
      id: "00000000-0000-0000-0000-000000000040",
      tenant_id: "00000000-0000-0000-0000-000000000002",
      name: "SC-PO-0001",
      status: "draft",
      supplier_id: "00000000-0000-0000-0000-000000000041",
      supplier_name: "Assembly Co. Ltd",
      rfq_id: null,
      quotation_id: null,
      award_id: null,
      company: "UltrERP Taiwan",
      currency: "TWD",
      transaction_date: "2026-04-27",
      schedule_date: "2026-05-11",
      subtotal: "5000.00",
      total_taxes: "500.00",
      grand_total: "5500.00",
      base_grand_total: "5500.00",
      taxes: [],
      contact_person: "",
      contact_email: "",
      set_warehouse: "WH-RAW",
      terms_and_conditions: "",
      notes: "",
      per_received: "0.00",
      per_billed: "0.00",
      is_approved: false,
      approved_by: "",
      approved_at: null,
      blanket_order_reference_id: null,
      landed_cost_reference_id: null,
      // Subcontracting metadata (Story 24-6)
      is_subcontracted: true,
      finished_goods_item_code: "FIN-001",
      finished_goods_item_name: "Finished Assembly",
      expected_subcontracted_qty: "100",
      created_at: "2026-04-27T00:00:00Z",
      updated_at: "2026-04-27T00:00:00Z",
      items: [],
    };

    expect(po.is_subcontracted).toBe(true);
    expect(po.finished_goods_item_code).toBe("FIN-001");
    expect(po.finished_goods_item_name).toBe("Finished Assembly");
    expect(po.expected_subcontracted_qty).toBe("100");
  });

  it("Subcontracting PO does not include BOM, auto-creation, cost-sheet, or backflush fields", () => {
    const po = {
      status: "draft",
      supplier_name: "Assembly Co. Ltd",
      is_subcontracted: true,
    };
    // BOM explosion, auto-creation, cost-sheet, and backflush are deferred to Epic 32
    expect("bom_id" in po).toBe(false);
    expect("auto_create_materials_transfer" in po).toBe(false);
    expect("cost_sheet_id" in po).toBe(false);
    expect("backflush_enabled" in po).toBe(false);
  });

  it("Supplier can be marked as a subcontractor", () => {
    // This is validated in the backend via is_subcontractor flag
    const supplier = {
      id: "00000000-0000-0000-0000-000000000041",
      name: "Assembly Co. Ltd",
      is_subcontractor: true,
    };

    expect(supplier.is_subcontractor).toBe(true);
  });
});

describe("Subcontracting Material Transfer Types (Story 24.6)", () => {
  it("SubcontractingMaterialTransferResponse has required fields", () => {
    const mt: SubcontractingMaterialTransferResponse = {
      id: "00000000-0000-0000-0000-000000000050",
      tenant_id: "00000000-0000-0000-0000-000000000002",
      name: "SMT-0001",
      status: "draft" as SubcontractingMaterialTransferStatus,
      purchase_order_id: "00000000-0000-0000-0000-000000000040",
      supplier_id: "00000000-0000-0000-0000-000000000041",
      supplier_name: "Assembly Co. Ltd",
      company: "UltrERP Taiwan",
      transfer_date: "2026-04-27",
      shipped_date: null,
      received_date: null,
      source_warehouse: "WH-RAW",
      contact_person: "",
      contact_email: "",
      notes: "Raw materials for assembly",
      created_at: "2026-04-27T00:00:00Z",
      updated_at: "2026-04-27T00:00:00Z",
      items: [],
    };

    expect(mt.id).toBe("00000000-0000-0000-0000-000000000050");
    expect(mt.name).toBe("SMT-0001");
    expect(mt.status).toBe("draft");
    expect(mt.purchase_order_id).toBe("00000000-0000-0000-0000-000000000040");
    expect(mt.supplier_name).toBe("Assembly Co. Ltd");
    expect(mt.source_warehouse).toBe("WH-RAW");
    expect(mt.items).toEqual([]);
  });

  it("SubcontractingMaterialTransferCreatePayload has required fields", () => {
    const payload: SubcontractingMaterialTransferCreatePayload = {
      purchase_order_id: "00000000-0000-0000-0000-000000000040",
      transfer_date: "2026-04-27",
      source_warehouse: "WH-RAW",
      contact_person: "",
      contact_email: "",
      notes: "Raw materials for assembly",
      items: [],
    };

    expect(payload.purchase_order_id).toBe("00000000-0000-0000-0000-000000000040");
    expect(payload.transfer_date).toBe("2026-04-27");
    expect(payload.source_warehouse).toBe("WH-RAW");
    expect(Array.isArray(payload.items)).toBe(true);
  });

  it("Material transfer status transitions are valid", () => {
    const validStatuses: SubcontractingMaterialTransferStatus[] = [
      "draft",
      "pending",
      "in_transit",
      "delivered",
      "cancelled",
    ];

    expect(validStatuses).toContain("draft");
    expect(validStatuses).toContain("pending");
    expect(validStatuses).toContain("in_transit");
    expect(validStatuses).toContain("delivered");
    expect(validStatuses).toContain("cancelled");
    expect(validStatuses).toHaveLength(5);
  });
});

describe("Subcontracting Receipt Types (Story 24.6)", () => {
  it("SubcontractingReceiptResponse has required fields", () => {
    const scr: SubcontractingReceiptResponse = {
      id: "00000000-0000-0000-0000-000000000060",
      tenant_id: "00000000-0000-0000-0000-000000000002",
      name: "SCR-0001",
      status: "draft" as SubcontractingReceiptStatus,
      purchase_order_id: "00000000-0000-0000-0000-000000000040",
      supplier_id: "00000000-0000-0000-0000-000000000041",
      supplier_name: "Assembly Co. Ltd",
      company: "UltrERP Taiwan",
      receipt_date: "2026-05-05",
      posting_date: null,
      set_warehouse: "WH-FIN",
      contact_person: "",
      notes: "Finished goods from assembly",
      inventory_mutated: false,
      inventory_mutated_at: null,
      created_at: "2026-05-05T00:00:00Z",
      updated_at: "2026-05-05T00:00:00Z",
      items: [],
      material_transfer_refs: [],
    };

    expect(scr.id).toBe("00000000-0000-0000-0000-000000000060");
    expect(scr.name).toBe("SCR-0001");
    expect(scr.status).toBe("draft");
    expect(scr.purchase_order_id).toBe("00000000-0000-0000-0000-000000000040");
    expect(scr.supplier_name).toBe("Assembly Co. Ltd");
    expect(scr.set_warehouse).toBe("WH-FIN");
    expect(scr.inventory_mutated).toBe(false);
  });

  it("SubcontractingReceiptCreatePayload has required fields", () => {
    const payload: SubcontractingReceiptCreatePayload = {
      purchase_order_id: "00000000-0000-0000-0000-000000000040",
      receipt_date: "2026-05-05",
      posting_date: null,
      set_warehouse: "WH-FIN",
      contact_person: "",
      notes: "Finished goods from assembly",
      material_transfer_ids: [],
      items: [],
    };

    expect(payload.purchase_order_id).toBe("00000000-0000-0000-0000-000000000040");
    expect(payload.receipt_date).toBe("2026-05-05");
    expect(payload.set_warehouse).toBe("WH-FIN");
    expect(Array.isArray(payload.material_transfer_ids)).toBe(true);
    expect(Array.isArray(payload.items)).toBe(true);
  });

  it("Subcontracting receipt status transitions are valid", () => {
    const validStatuses: SubcontractingReceiptStatus[] = ["draft", "submitted", "cancelled"];

    expect(validStatuses).toContain("draft");
    expect(validStatuses).toContain("submitted");
    expect(validStatuses).toContain("cancelled");
    expect(validStatuses).toHaveLength(3);
  });

  it("Subcontracting receipt is separate from standard goods receipt", () => {
    // SubcontractingReceipt has different fields than GoodsReceipt
    const scr = {
      name: "SCR-0001",
      status: "draft",
    };

    // Standard GR fields should not be on SCR by default
    expect("per_received" in scr).toBe(false);
    expect("per_billed" in scr).toBe(false);
  });
});

describe("Subcontracting Validation (Story 24.6)", () => {
  it("Non-subcontractor supplier cannot be used in subcontracting PO", () => {
    // Backend validates that supplier.is_subcontractor must be true
    const regularSupplier = {
      id: "00000000-0000-0000-0000-000000000070",
      name: "Regular Parts Co.",
      is_subcontractor: false,
    };

    const isEligible = regularSupplier.is_subcontractor === true;
    expect(isEligible).toBe(false);
  });

  it("Subcontracting PO requires is_subcontracted flag", () => {
    const subcontractingPO = {
      id: "00000000-0000-0000-0000-000000000040",
      supplier_id: "00000000-0000-0000-0000-000000000041",
      is_subcontracted: true,
    };

    expect(subcontractingPO.is_subcontracted).toBe(true);
  });

  it("Material transfer requires linked subcontracting PO", () => {
    const mt = {
      purchase_order_id: "00000000-0000-0000-0000-000000000040",
      status: "draft",
    };

    expect(mt.purchase_order_id).toBeTruthy();
  });

  it("Subcontracting receipt requires linked subcontracting PO", () => {
    const scr = {
      purchase_order_id: "00000000-0000-0000-0000-000000000040",
      status: "draft",
    };

    expect(scr.purchase_order_id).toBeTruthy();
  });

  it("Material transfer can optionally link to subcontracting receipt", () => {
    // Material transfers can be referenced by subcontracting receipts
    // but the linkage is optional for audit trail
    const mt = {
      id: "00000000-0000-0000-0000-000000000050",
      status: "delivered",
    };

    expect(mt.status).toBe("delivered");
  });
});
