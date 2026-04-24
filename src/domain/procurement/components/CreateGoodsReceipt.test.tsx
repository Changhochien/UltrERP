import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { CreateGoodsReceipt } from "./CreateGoodsReceipt";

const navigateMock = vi.fn();
const createGRMock = vi.fn();
const purchaseOrderMock = vi.hoisted(() => ({
  data: {
    id: "po-1",
    name: "PO-0001",
    supplier_name: "Alpha Parts Co.",
    set_warehouse: "MAIN-WH",
    items: [
      {
        id: "po-line-1",
        item_code: "MAT-001",
        item_name: "Industrial Bearing",
        description: "6205-2RS sealed bearing",
        qty: "5",
        received_qty: "0",
        uom: "PCS",
        warehouse: "MAIN-WH",
        unit_rate: "100.00",
      },
    ],
  },
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("../hooks/usePurchaseOrder", () => ({
  usePurchaseOrder: () => ({
    data: purchaseOrderMock.data,
    loading: false,
    error: null,
  }),
}));

vi.mock("../hooks/useGoodsReceipt", () => ({
  useGoodsReceiptActions: () => ({
    create: createGRMock,
  }),
}));

afterEach(() => {
  cleanup();
  navigateMock.mockReset();
  createGRMock.mockReset();
});

describe("CreateGoodsReceipt", () => {
  it("submits rejected warehouse and exception notes when a line has rejected quantity", async () => {
    createGRMock.mockResolvedValue({ id: "gr-1" });

    render(<CreateGoodsReceipt purchaseOrderId="po-1" />);

    fireEvent.change(screen.getByLabelText("Accepted quantity for line 1"), {
      target: { value: "3" },
    });
    fireEvent.change(screen.getByLabelText("Rejected quantity for line 1"), {
      target: { value: "2" },
    });
    fireEvent.change(screen.getByLabelText("Rejected warehouse for line 1"), {
      target: { value: "REJECT-WH" },
    });
    fireEvent.change(screen.getByLabelText("Exception notes for line 1"), {
      target: { value: "Damaged packaging" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Create Receipt" }));

    await waitFor(() => {
      expect(createGRMock).toHaveBeenCalledTimes(1);
    });

    expect(createGRMock).toHaveBeenCalledWith({
      purchase_order_id: "po-1",
      transaction_date: expect.any(String),
      set_warehouse: "MAIN-WH",
      contact_person: "",
      notes: "",
      items: [
        {
          purchase_order_item_id: "po-line-1",
          item_code: "MAT-001",
          item_name: "Industrial Bearing",
          description: "6205-2RS sealed bearing",
          accepted_qty: "3",
          rejected_qty: "2",
          uom: "PCS",
          warehouse: "MAIN-WH",
          rejected_warehouse: "REJECT-WH",
          batch_no: "",
          serial_no: "",
          exception_notes: "Damaged packaging",
          unit_rate: "100.00",
        },
      ],
    });
    expect(navigateMock).toHaveBeenCalledWith("/procurement/goods-receipts/gr-1");
  });
});