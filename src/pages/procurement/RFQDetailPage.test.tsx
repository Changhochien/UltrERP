import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const rfqHooksMock = vi.hoisted(() => ({
  refetchRFQ: vi.fn(),
  refetchComparison: vi.fn(),
  submit: vi.fn(),
}));

const quotationHooksMock = vi.hoisted(() => ({
  award: vi.fn(),
  refetchAward: vi.fn(),
  existingAward: null as null | {
    id: string;
    awarded_supplier_name: string;
  },
}));

const toastMock = vi.hoisted(() => ({
  toast: vi.fn(),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, params?: { supplier?: string }) =>
      params?.supplier ? `${key}:${params.supplier}` : key,
  }),
}));

vi.mock("../../components/layout/PageLayout", () => ({
  PageHeader: ({ title, description }: { title: string; description?: string }) => (
    <div>
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
  ),
}));

vi.mock("../../components/ui/badge", () => ({
  Badge: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
}));

vi.mock("../../components/ui/button", () => ({
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

vi.mock("../../components/ui/input", () => ({
  Input: (props: React.InputHTMLAttributes<HTMLInputElement>) => <input {...props} />,
}));

vi.mock("../../components/ui/StatusBadge", () => ({
  StatusBadge: ({ status }: { status: string }) => <span>{status}</span>,
}));

vi.mock("../../hooks/useToast", () => ({
  useToast: () => toastMock,
}));

vi.mock("../../domain/procurement/hooks/useRFQ", () => ({
  useRFQ: () => ({
    rfq: {
      id: "rfq-123",
      name: "PRQ-0001",
      status: "submitted",
      company: "UltrERP Taiwan",
      currency: "TWD",
      items: [],
      suppliers: [],
    },
    loading: false,
    error: null,
    refetch: rfqHooksMock.refetchRFQ,
  }),
  useRFQComparison: () => ({
    data: {
      rfq_id: "rfq-123",
      rfq_name: "PRQ-0001",
      status: "submitted",
      items: [],
      quotations: [
        {
          quotation_id: "quote-001",
          supplier_name: "Alpha Parts Co.",
          currency: "TWD",
          grand_total: "12500.00",
          base_grand_total: "12500.00",
          comparison_base_total: "12500.00",
          lead_time_days: 14,
          valid_till: "2026-05-15",
          is_awarded: false,
          is_expired: false,
          status: "submitted",
          items: [],
        },
      ],
    },
    refetch: rfqHooksMock.refetchComparison,
  }),
  useSubmitRFQ: () => ({
    submit: rfqHooksMock.submit,
    loading: false,
  }),
}));

vi.mock("../../domain/procurement/hooks/useSupplierQuotation", () => ({
  useAward: () => ({
    award: quotationHooksMock.award,
    loading: false,
    error: null,
  }),
  useRFQAward: () => ({
    award: quotationHooksMock.existingAward,
    loading: false,
    error: null,
    refetch: quotationHooksMock.refetchAward,
  }),
}));

vi.mock("../../lib/api/procurement", () => ({
  createSupplierQuotation: vi.fn(),
}));

afterEach(() => {
  cleanup();
  rfqHooksMock.refetchRFQ.mockReset();
  rfqHooksMock.refetchComparison.mockReset();
  rfqHooksMock.submit.mockReset();
  quotationHooksMock.award.mockReset();
  quotationHooksMock.refetchAward.mockReset();
  quotationHooksMock.existingAward = null;
  toastMock.toast.mockReset();
});

describe("RFQDetailPage", () => {
  it("refetches award state after selecting a winning quotation", async () => {
    quotationHooksMock.award.mockResolvedValue({
      rfq_id: "rfq-123",
      quotation_id: "quote-001",
    });

    const { RFQDetailPage } = await import("./RFQDetailPage");

    render(
      <MemoryRouter initialEntries={["/procurement/rfqs/rfq-123"]}>
        <Routes>
          <Route path="/procurement/rfqs/:rfqId" element={<RFQDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "procurement.rfq.tabs.compare" }));
    fireEvent.click(screen.getByRole("button", { name: "procurement.award.selectAsWinner" }));

    await waitFor(() => {
      expect(quotationHooksMock.award).toHaveBeenCalledWith({
        rfq_id: "rfq-123",
        quotation_id: "quote-001",
        awarded_by: "buyer",
      });
      expect(rfqHooksMock.refetchComparison).toHaveBeenCalledTimes(1);
      expect(quotationHooksMock.refetchAward).toHaveBeenCalledTimes(1);
      expect(toastMock.toast).toHaveBeenCalledWith({
        title: "procurement.award.success",
        variant: "success",
      });
    });
  });

  it("shows a create purchase order handoff when an award already exists", async () => {
    quotationHooksMock.existingAward = {
      id: "award-123",
      awarded_supplier_name: "Alpha Parts Co.",
    };

    const { RFQDetailPage } = await import("./RFQDetailPage");

    render(
      <MemoryRouter initialEntries={["/procurement/rfqs/rfq-123"]}>
        <Routes>
          <Route path="/procurement/rfqs/:rfqId" element={<RFQDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "procurement.rfq.tabs.compare" }));

    expect(
      screen.getByRole("link", { name: "procurement.award.createPurchaseOrder" }).getAttribute("href"),
    ).toBe("/procurement/purchase-orders/new?awardId=award-123");
  });
});