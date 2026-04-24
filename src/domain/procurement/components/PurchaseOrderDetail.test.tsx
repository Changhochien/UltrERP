import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { PurchaseOrderDetail } from "./PurchaseOrderDetail";

const navigateMock = vi.fn();
const refetchMock = vi.fn();
const purchaseOrderBase = vi.hoisted(() => ({
  id: "po-1",
  tenant_id: "tenant-1",
  supplier_id: "sup-1",
  name: "PO-0001",
  status: "to_receive",
  is_approved: true,
  created_at: "2026-04-24T08:00:00Z",
  updated_at: "2026-04-24T08:00:00Z",
  rfq_id: null,
  quotation_id: null,
  award_id: null,
  supplier_name: "Alpha Parts Co.",
  company: "UltrERP Taiwan",
  currency: "TWD",
  transaction_date: "2026-04-24T00:00:00Z",
  schedule_date: "2026-04-28T00:00:00Z",
  subtotal: "500",
  total_taxes: "25",
  grand_total: "525",
  base_grand_total: "525",
  taxes: [],
  contact_person: "",
  contact_email: "buyer@alpha.example",
  set_warehouse: "",
  terms_and_conditions: "",
  notes: "Handle partial receipts separately.",
  per_received: "40",
  per_billed: "0",
  approved_by: "",
  approved_at: null,
  blanket_order_reference_id: null,
  landed_cost_reference_id: null,
  is_subcontracted: false,
  finished_goods_item_code: null,
  finished_goods_item_name: null,
  expected_subcontracted_qty: null,
  items: [
    {
      id: "po-line-1",
      purchase_order_id: "po-1",
      idx: 1,
      quotation_item_id: null,
      rfq_item_id: null,
      item_code: "MAT-001",
      item_name: "Industrial Bearing",
      description: "6205-2RS sealed bearing",
      qty: "5",
      uom: "PCS",
      warehouse: "MAIN-WH",
      unit_rate: "100",
      amount: "500",
      tax_rate: "0",
      tax_amount: "0",
      tax_code: "",
      received_qty: "2",
      billed_amount: "0",
      created_at: "2026-04-24T08:00:00Z",
    },
  ],
}));
const receiptsMock = vi.hoisted(() => ({
  items: [
    {
      id: "gr-1",
      name: "GR-0001",
      status: "submitted",
      purchase_order_id: "po-1",
      supplier_name: "Alpha Parts Co.",
      transaction_date: "2026-04-24T00:00:00Z",
      posting_date: null,
      inventory_mutated: true,
      created_at: "2026-04-24T08:30:00Z",
    },
    {
      id: "gr-2",
      name: "GR-0002",
      status: "draft",
      purchase_order_id: "po-1",
      supplier_name: "Alpha Parts Co.",
      transaction_date: "2026-04-25T00:00:00Z",
      posting_date: null,
      inventory_mutated: false,
      created_at: "2026-04-25T09:00:00Z",
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
  pages: 1,
}));
const cleanSupplierControls = vi.hoisted(() => ({
  supplier_id: "sup-1",
  supplier_name: "Alpha Parts Co.",
  is_active: true,
  is_subcontractor: false,
  on_hold: false,
  hold_type: null,
  release_date: null,
  is_effectively_on_hold: false,
  scorecard_standing: null,
  scorecard_last_evaluated_at: null,
  warn_rfqs: false,
  prevent_rfqs: false,
  rfq_blocked: false,
  rfq_warned: false,
  rfq_control_reason: "",
  warn_pos: false,
  prevent_pos: false,
  po_blocked: false,
  po_warned: false,
  po_control_reason: "",
}));
const actionMocks = vi.hoisted(() => ({
  createFromAward: vi.fn(),
  update: vi.fn(),
  submit: vi.fn(),
  hold: vi.fn(),
  release: vi.fn(),
  complete: vi.fn(),
  cancel: vi.fn(),
  close: vi.fn(),
}));

let currentPurchaseOrder = purchaseOrderBase;
let currentSupplierControls = cleanSupplierControls;

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useParams: () => ({ poId: "po-1" }),
    useNavigate: () => navigateMock,
  };
});

vi.mock("../hooks/usePurchaseOrder", () => ({
  usePurchaseOrder: () => ({
    data: currentPurchaseOrder,
    loading: false,
    error: null,
    refetch: refetchMock,
  }),
  usePurchaseOrderActions: () => actionMocks,
}));

vi.mock("../hooks/useGoodsReceipt", () => ({
  useReceiptsForPO: () => ({
    data: receiptsMock,
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock("../hooks/useSupplierControls", () => ({
  useSupplierControls: () => ({
    data: currentSupplierControls,
    loading: false,
    error: null,
  }),
}));

vi.mock("./DownstreamInvoiceLineage", () => ({
  DownstreamInvoiceLineage: ({
    type,
    documentId,
    onInvoiceClick,
  }: {
    type: string;
    documentId: string;
    onInvoiceClick?: (invoiceId: string) => void;
  }) => (
    <button onClick={() => onInvoiceClick?.("inv-1")}>{`Downstream lineage ${type}:${documentId}`}</button>
  ),
}));

afterEach(() => {
  cleanup();
  currentPurchaseOrder = purchaseOrderBase;
  currentSupplierControls = cleanSupplierControls;
  navigateMock.mockReset();
  refetchMock.mockReset();
  Object.values(actionMocks).forEach((mockFn) => mockFn.mockReset());
});

describe("PurchaseOrderDetail", () => {
  it("shows remaining open quantity and receipt history on the PO detail view", () => {
    render(
      <MemoryRouter>
        <PurchaseOrderDetail />
      </MemoryRouter>,
    );

    screen.getByText("Open Qty");
    screen.getByText("3 PCS");
    screen.getByText("Receipt History");
    screen.getByText("2 receipts recorded against this PO.");
    screen.getByText("GR-0001");
    screen.getByText("GR-0002");
    screen.getByText("Downstream Invoices");

    fireEvent.click(screen.getByRole("button", { name: "Downstream lineage purchase_order:po-1" }));

    expect(navigateMock).toHaveBeenCalledWith("/purchases", {
      state: { selectedInvoiceId: "inv-1" },
    });
  });

  it("surfaces supplier controls and saves draft subcontracting procurement options", () => {
    currentPurchaseOrder = {
      ...purchaseOrderBase,
      status: "draft",
      is_approved: false,
      per_received: "0",
      per_billed: "0",
      notes: "Draft subcontracting PO.",
    };
    currentSupplierControls = {
      ...cleanSupplierControls,
      is_subcontractor: true,
      po_blocked: true,
      prevent_pos: true,
      po_control_reason: "Supplier is on hold for subcontracting review.",
    };
    actionMocks.update.mockResolvedValue({
      ...currentPurchaseOrder,
      is_subcontracted: true,
      finished_goods_item_code: "FG-100",
      finished_goods_item_name: "Finished Gearbox",
      expected_subcontracted_qty: "12",
      blanket_order_reference_id: "BO-42",
      landed_cost_reference_id: "LC-9",
    });

    render(
      <MemoryRouter>
        <PurchaseOrderDetail />
      </MemoryRouter>,
    );

    screen.getByText("Supplier Controls");
    screen.getByText("Procurement Options");
    expect(screen.getByRole("alert").textContent).toContain("Supplier is on hold for subcontracting review.");
    expect((screen.getByRole("button", { name: "Submit for Approval" }) as HTMLButtonElement).disabled).toBe(true);

    fireEvent.click(screen.getByLabelText("Subcontracting purchase order"));
    fireEvent.change(screen.getByLabelText("Finished Goods Item Code"), { target: { value: "FG-100" } });
    fireEvent.change(screen.getByLabelText("Finished Goods Item Name"), { target: { value: "Finished Gearbox" } });
    fireEvent.change(screen.getByLabelText("Expected Subcontracted Quantity"), { target: { value: "12" } });
    fireEvent.change(screen.getByLabelText("Blanket Order Reference"), { target: { value: "BO-42" } });
    fireEvent.change(screen.getByLabelText("Landed Cost Reference"), { target: { value: "LC-9" } });

    fireEvent.click(screen.getByRole("button", { name: "Save Procurement Options" }));

    expect(actionMocks.update).toHaveBeenCalledWith("po-1", {
      is_subcontracted: true,
      finished_goods_item_code: "FG-100",
      finished_goods_item_name: "Finished Gearbox",
      expected_subcontracted_qty: "12",
      blanket_order_reference_id: "BO-42",
      landed_cost_reference_id: "LC-9",
    });
  });
});