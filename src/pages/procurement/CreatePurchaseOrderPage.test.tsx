import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const poDetailMock = vi.hoisted(() => ({
  lastAwardId: null as string | null,
  lastIsNew: false,
}));

vi.mock("@/domain/procurement/components/PurchaseOrderDetail", () => ({
  PurchaseOrderDetail: ({ isNew = false, awardId }: { isNew?: boolean; awardId?: string | null }) => {
    poDetailMock.lastIsNew = isNew;
    poDetailMock.lastAwardId = awardId ?? null;
    return <div>purchase-order-detail</div>;
  },
}));

afterEach(() => {
  cleanup();
  poDetailMock.lastAwardId = null;
  poDetailMock.lastIsNew = false;
});

describe("CreatePurchaseOrderPage", () => {
  it("shows guidance when no awardId is provided", async () => {
    const { CreatePurchaseOrderPage } = await import("./CreatePurchaseOrderPage");

    render(
      <MemoryRouter initialEntries={["/procurement/purchase-orders/new"]}>
        <Routes>
          <Route path="/procurement/purchase-orders/new" element={<CreatePurchaseOrderPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Create Purchase Order")).toBeTruthy();
    expect(screen.getByText("Select a winning supplier quotation from an RFQ before creating a purchase order.")).toBeTruthy();
    expect(
      screen.getByRole("link", { name: "Return to sourcing workspace" }).getAttribute("href"),
    ).toBe("/procurement");
  });

  it("forwards the awardId into the purchase order detail create flow", async () => {
    const { CreatePurchaseOrderPage } = await import("./CreatePurchaseOrderPage");

    render(
      <MemoryRouter initialEntries={["/procurement/purchase-orders/new?awardId=award-123"]}>
        <Routes>
          <Route path="/procurement/purchase-orders/new" element={<CreatePurchaseOrderPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("purchase-order-detail")).toBeTruthy();
    expect(poDetailMock.lastIsNew).toBe(true);
    expect(poDetailMock.lastAwardId).toBe("award-123");
  });
});