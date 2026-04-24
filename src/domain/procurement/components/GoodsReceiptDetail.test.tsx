import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { GoodsReceiptDetail } from "./GoodsReceiptDetail";

const navigateMock = vi.fn();
const refetchMock = vi.fn();
const goodsReceiptMock = vi.hoisted(() => ({
  id: "gr-1",
  tenant_id: "tenant-1",
  name: "GR-0001",
  status: "submitted",
  purchase_order_id: "po-1",
  supplier_id: "sup-1",
  supplier_name: "Alpha Parts Co.",
  company: "UltrERP Taiwan",
  transaction_date: "2026-04-24T00:00:00Z",
  posting_date: "2026-04-24T00:00:00Z",
  set_warehouse: "MAIN-WH",
  contact_person: "",
  notes: "Dock 3 receiving.",
  inventory_mutated: true,
  inventory_mutated_at: "2026-04-24T08:00:00Z",
  created_at: "2026-04-24T08:00:00Z",
  updated_at: "2026-04-24T08:00:00Z",
  items: [
    {
      id: "gr-line-1",
      purchase_order_item_id: "po-line-1",
      item_code: "MAT-001",
      item_name: "Industrial Bearing",
      description: "6205-2RS sealed bearing",
      accepted_qty: "3",
      rejected_qty: "2",
      total_qty: "5",
      uom: "PCS",
      warehouse: "MAIN-WH",
      rejected_warehouse: "REJECT-WH",
      batch_no: "",
      serial_no: "",
      exception_notes: "Damaged packaging",
      is_rejected: true,
      unit_rate: "100",
      created_at: "2026-04-24T08:00:00Z",
    },
  ],
}));
const actionMocks = vi.hoisted(() => ({
  submit: vi.fn(),
  cancel: vi.fn(),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useParams: () => ({ grId: "gr-1" }),
    useNavigate: () => navigateMock,
  };
});

vi.mock("../hooks/useGoodsReceipt", () => ({
  useGoodsReceipt: () => ({
    data: goodsReceiptMock,
    loading: false,
    error: null,
    refetch: refetchMock,
  }),
  useGoodsReceiptActions: () => actionMocks,
  useReceiptsForPO: () => ({
    data: {
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
          created_at: "2026-04-24T08:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 100,
      pages: 1,
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock("./DownstreamInvoiceLineage", () => ({
  DownstreamInvoiceLineage: ({
    type,
    documentId,
    lineId,
    onInvoiceClick,
  }: {
    type: string;
    documentId: string;
    lineId?: string;
    onInvoiceClick?: (invoiceId: string) => void;
  }) => (
    <button onClick={() => onInvoiceClick?.("inv-2")}>{`Downstream lineage ${type}:${documentId}:${lineId ?? ""}`}</button>
  ),
}));

afterEach(() => {
  cleanup();
  navigateMock.mockReset();
  refetchMock.mockReset();
  actionMocks.submit.mockReset();
  actionMocks.cancel.mockReset();
});

describe("GoodsReceiptDetail", () => {
  it("shows downstream invoice lineage for each goods receipt line", () => {
    render(
      <MemoryRouter>
        <GoodsReceiptDetail />
      </MemoryRouter>,
    );

    screen.getByText("Downstream Invoice Lineage");

    fireEvent.click(screen.getByRole("button", { name: "Downstream lineage goods_receipt_line:gr-1:gr-line-1" }));

    expect(navigateMock).toHaveBeenCalledWith("/purchases", {
      state: { selectedInvoiceId: "inv-2" },
    });
  });
});