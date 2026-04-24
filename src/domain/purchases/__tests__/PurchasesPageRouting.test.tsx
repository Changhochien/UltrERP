import { describe, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { PurchasesPage } from "../../../pages/PurchasesPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../../../domain/purchases/components/SupplierInvoiceList", () => ({
  SupplierInvoiceList: () => <div>Supplier invoice list mock</div>,
}));

vi.mock("../../../domain/purchases/components/SupplierInvoiceDetail", () => ({
  SupplierInvoiceDetail: ({ invoiceId }: { invoiceId: string }) => (
    <div>{`Supplier invoice detail mock:${invoiceId}`}</div>
  ),
}));

describe("PurchasesPage routing", () => {
  it("opens the requested invoice detail when navigation state provides a selected invoice id", () => {
    render(
      <MemoryRouter initialEntries={[{ pathname: "/purchases", state: { selectedInvoiceId: "sup-inv-42" } }]}>
        <PurchasesPage />
      </MemoryRouter>,
    );

    screen.getByText("Supplier invoice detail mock:sup-inv-42");
  });
});