import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import type { PurchaseOrderResponse } from "../types";

const listTransfersMock = vi.hoisted(() => vi.fn());
const getTransferMock = vi.hoisted(() => vi.fn());
const createTransferMock = vi.hoisted(() => vi.fn());
const submitTransferMock = vi.hoisted(() => vi.fn());
const shipTransferMock = vi.hoisted(() => vi.fn());
const deliverTransferMock = vi.hoisted(() => vi.fn());
const cancelTransferMock = vi.hoisted(() => vi.fn());
const listReceiptsMock = vi.hoisted(() => vi.fn());
const getReceiptMock = vi.hoisted(() => vi.fn());
const createReceiptMock = vi.hoisted(() => vi.fn());
const submitReceiptMock = vi.hoisted(() => vi.fn());
const cancelReceiptMock = vi.hoisted(() => vi.fn());

vi.mock("../../../components/ui/button", () => ({
  Button: ({
    children,
    onClick,
    disabled,
    type = "button",
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
    type?: "button" | "submit";
  }) => (
    <button type={type} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  ),
}));

vi.mock("../../../lib/api/procurement", () => ({
  listSubcontractingMaterialTransfers: listTransfersMock,
  getSubcontractingMaterialTransfer: getTransferMock,
  createSubcontractingMaterialTransfer: createTransferMock,
  submitSubcontractingMaterialTransfer: submitTransferMock,
  shipSubcontractingMaterialTransfer: shipTransferMock,
  deliverSubcontractingMaterialTransfer: deliverTransferMock,
  cancelSubcontractingMaterialTransfer: cancelTransferMock,
  listSubcontractingReceipts: listReceiptsMock,
  getSubcontractingReceipt: getReceiptMock,
  createSubcontractingReceipt: createReceiptMock,
  submitSubcontractingReceipt: submitReceiptMock,
  cancelSubcontractingReceipt: cancelReceiptMock,
}));

const subcontractingPo: PurchaseOrderResponse = {
  id: "po-1",
  tenant_id: "tenant-1",
  name: "PO-0001",
  status: "draft",
  supplier_id: "sup-1",
  supplier_name: "Assembly Co. Ltd",
  rfq_id: null,
  quotation_id: null,
  award_id: null,
  company: "UltrERP Taiwan",
  currency: "TWD",
  transaction_date: "2026-05-01",
  schedule_date: "2026-05-05",
  subtotal: "1200",
  total_taxes: "60",
  grand_total: "1260",
  base_grand_total: "1260",
  taxes: [],
  contact_person: "Buyer Chen",
  contact_email: "buyer@example.com",
  set_warehouse: "FG-WH",
  terms_and_conditions: "",
  notes: "Subcontract gearbox assembly",
  per_received: "0",
  per_billed: "0",
  is_approved: false,
  approved_by: "",
  approved_at: null,
  blanket_order_reference_id: null,
  landed_cost_reference_id: null,
  is_subcontracted: true,
  finished_goods_item_code: "FG-100",
  finished_goods_item_name: "Finished Gearbox",
  expected_subcontracted_qty: "12",
  created_at: "2026-05-01T00:00:00Z",
  updated_at: "2026-05-01T00:00:00Z",
  items: [
    {
      id: "po-line-1",
      purchase_order_id: "po-1",
      idx: 1,
      quotation_item_id: null,
      rfq_item_id: null,
      item_code: "FG-100",
      item_name: "Finished Gearbox",
      description: "Assembly service",
      qty: "12",
      uom: "PCS",
      warehouse: "FG-WH",
      unit_rate: "100",
      amount: "1200",
      tax_rate: "0",
      tax_amount: "0",
      tax_code: "",
      received_qty: "0",
      billed_amount: "0",
      created_at: "2026-05-01T00:00:00Z",
    },
  ],
};

afterEach(() => {
  cleanup();
  listTransfersMock.mockReset();
  getTransferMock.mockReset();
  createTransferMock.mockReset();
  submitTransferMock.mockReset();
  shipTransferMock.mockReset();
  deliverTransferMock.mockReset();
  cancelTransferMock.mockReset();
  listReceiptsMock.mockReset();
  getReceiptMock.mockReset();
  createReceiptMock.mockReset();
  submitReceiptMock.mockReset();
  cancelReceiptMock.mockReset();
});

describe("SubcontractingWorkflowPanel", () => {
  it("shows transfer status and receipt linkage audit details", async () => {
    listTransfersMock.mockResolvedValue({
      items: [{ id: "mt-1" }],
      total: 1,
      page: 1,
      page_size: 50,
      pages: 1,
    });
    getTransferMock.mockResolvedValue({
      id: "mt-1",
      tenant_id: "tenant-1",
      name: "SMT-0001",
      status: "in_transit",
      purchase_order_id: "po-1",
      supplier_id: "sup-1",
      supplier_name: "Assembly Co. Ltd",
      company: "UltrERP Taiwan",
      transfer_date: "2026-05-02",
      shipped_date: "2026-05-03",
      received_date: null,
      source_warehouse: "RAW-WH",
      contact_person: "Buyer Chen",
      contact_email: "buyer@example.com",
      notes: "Steel and seals",
      created_at: "2026-05-02T00:00:00Z",
      updated_at: "2026-05-03T00:00:00Z",
      items: [
        {
          id: "mt-line-1",
          material_transfer_id: "mt-1",
          idx: 1,
          item_code: "RAW-1",
          item_name: "Gear Blank",
          description: "",
          qty: "12",
          uom: "PCS",
          warehouse: "RAW-WH",
          created_at: "2026-05-02T00:00:00Z",
        },
      ],
    });
    listReceiptsMock.mockResolvedValue({
      items: [{ id: "scr-1" }],
      total: 1,
      page: 1,
      page_size: 50,
      pages: 1,
    });
    getReceiptMock.mockResolvedValue({
      id: "scr-1",
      tenant_id: "tenant-1",
      name: "SCR-0001",
      status: "submitted",
      purchase_order_id: "po-1",
      supplier_id: "sup-1",
      supplier_name: "Assembly Co. Ltd",
      company: "UltrERP Taiwan",
      receipt_date: "2026-05-05",
      posting_date: "2026-05-05",
      set_warehouse: "FG-WH",
      contact_person: "Buyer Chen",
      notes: "Finished units received",
      inventory_mutated: true,
      inventory_mutated_at: "2026-05-05T08:00:00Z",
      created_at: "2026-05-05T00:00:00Z",
      updated_at: "2026-05-05T08:00:00Z",
      items: [
        {
          id: "scr-line-1",
          subcontracting_receipt_id: "scr-1",
          idx: 1,
          item_code: "FG-100",
          item_name: "Finished Gearbox",
          description: "",
          accepted_qty: "12",
          rejected_qty: "0",
          total_qty: "12",
          uom: "PCS",
          warehouse: "FG-WH",
          unit_rate: "100",
          exception_notes: "",
          is_rejected: false,
          created_at: "2026-05-05T00:00:00Z",
        },
      ],
      material_transfer_refs: [
        {
          id: "ref-1",
          subcontracting_receipt_id: "scr-1",
          material_transfer_id: "mt-1",
          created_at: "2026-05-05T00:00:00Z",
        },
      ],
    });

    const { SubcontractingWorkflowPanel } = await import("./SubcontractingWorkflowPanel");

    render(<SubcontractingWorkflowPanel po={subcontractingPo} />);

    await waitFor(() => {
      expect(screen.getByText("SMT-0001")).toBeTruthy();
      expect(screen.getByText("SCR-0001")).toBeTruthy();
    });

    expect(screen.getByText("Linked transfers: SMT-0001")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Mark Delivered" })).toBeTruthy();
  });

  it("creates a material transfer from the PO detail panel", async () => {
    listTransfersMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50, pages: 0 });
    listReceiptsMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50, pages: 0 });
    createTransferMock.mockResolvedValue({ id: "mt-1" });

    const { SubcontractingWorkflowPanel } = await import("./SubcontractingWorkflowPanel");

    render(<SubcontractingWorkflowPanel po={subcontractingPo} />);

    await waitFor(() => {
      expect(listTransfersMock).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByRole("button", { name: "New Material Transfer" }));
    fireEvent.change(screen.getByLabelText("Source Warehouse"), { target: { value: "RAW-WH" } });
    fireEvent.change(screen.getByLabelText("Transfer Item Name 1"), { target: { value: "Gear Blank" } });
    fireEvent.change(screen.getByLabelText("Transfer Quantity 1"), { target: { value: "12" } });
    fireEvent.change(screen.getByLabelText("Transfer UOM 1"), { target: { value: "PCS" } });
    fireEvent.change(screen.getByLabelText("Transfer Item Warehouse 1"), { target: { value: "RAW-WH" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Material Transfer" }));

    await waitFor(() => {
      expect(createTransferMock).toHaveBeenCalledWith(
        expect.objectContaining({
          purchase_order_id: "po-1",
          source_warehouse: "RAW-WH",
          items: [
            expect.objectContaining({
              item_name: "Gear Blank",
              qty: "12",
              uom: "PCS",
              warehouse: "RAW-WH",
            }),
          ],
        }),
      );
    });
  });

  it("creates a subcontracting receipt linked to selected material transfers", async () => {
    listTransfersMock.mockResolvedValue({
      items: [{ id: "mt-1" }],
      total: 1,
      page: 1,
      page_size: 50,
      pages: 1,
    });
    getTransferMock.mockResolvedValue({
      id: "mt-1",
      tenant_id: "tenant-1",
      name: "SMT-0001",
      status: "delivered",
      purchase_order_id: "po-1",
      supplier_id: "sup-1",
      supplier_name: "Assembly Co. Ltd",
      company: "UltrERP Taiwan",
      transfer_date: "2026-05-02",
      shipped_date: "2026-05-03",
      received_date: "2026-05-04",
      source_warehouse: "RAW-WH",
      contact_person: "Buyer Chen",
      contact_email: "buyer@example.com",
      notes: "Steel and seals",
      created_at: "2026-05-02T00:00:00Z",
      updated_at: "2026-05-04T00:00:00Z",
      items: [],
    });
    listReceiptsMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50, pages: 0 });
    createReceiptMock.mockResolvedValue({ id: "scr-1" });

    const { SubcontractingWorkflowPanel } = await import("./SubcontractingWorkflowPanel");

    render(<SubcontractingWorkflowPanel po={subcontractingPo} />);

    await waitFor(() => {
      expect(getTransferMock).toHaveBeenCalledWith("mt-1");
      expect(
        (screen.getByRole("button", { name: "New Subcontracting Receipt" }) as HTMLButtonElement).disabled,
      ).toBe(false);
    });

    fireEvent.click(screen.getByRole("button", { name: "New Subcontracting Receipt" }));
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Create Subcontracting Receipt" }));

    await waitFor(() => {
      expect(createReceiptMock).toHaveBeenCalledWith(
        expect.objectContaining({
          purchase_order_id: "po-1",
          material_transfer_ids: ["mt-1"],
          items: [
            expect.objectContaining({
              item_code: "FG-100",
              item_name: "Finished Gearbox",
            }),
          ],
        }),
      );
    });
  });
});