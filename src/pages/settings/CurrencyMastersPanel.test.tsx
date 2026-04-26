import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CurrencyMastersPanel from "./CurrencyMastersPanel";
import {
  createExchangeRate,
  listCurrencies,
  listExchangeRates,
} from "../../lib/api/currencies";

const successToastMock = vi.fn();
const errorToastMock = vi.fn();

vi.mock("../../lib/api/currencies", () => ({
  listCurrencies: vi.fn(),
  listExchangeRates: vi.fn(),
  createCurrency: vi.fn(),
  updateCurrency: vi.fn(),
  setBaseCurrency: vi.fn(),
  createExchangeRate: vi.fn(),
  updateExchangeRate: vi.fn(),
}));

vi.mock("../../hooks/useToast", () => ({
  useToast: () => ({
    success: successToastMock,
    error: errorToastMock,
  }),
}));

vi.mock("../../hooks/useAuth", async () => {
  const actual = await vi.importActual<typeof import("../../hooks/useAuth")>("../../hooks/useAuth");
  return {
    ...actual,
    useOptionalAuth: () => ({ user: { role: "finance" } }),
  };
});

const mockedListCurrencies = vi.mocked(listCurrencies);
const mockedListExchangeRates = vi.mocked(listExchangeRates);
const mockedCreateExchangeRate = vi.mocked(createExchangeRate);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  mockedListCurrencies.mockResolvedValue({
    items: [
      {
        id: "currency-usd",
        tenant_id: "tenant-1",
        code: "USD",
        symbol: "$",
        decimal_places: 2,
        is_active: true,
        is_base_currency: false,
        created_at: "2026-04-26T00:00:00Z",
        updated_at: "2026-04-26T00:00:00Z",
      },
      {
        id: "currency-twd",
        tenant_id: "tenant-1",
        code: "TWD",
        symbol: "NT$",
        decimal_places: 0,
        is_active: true,
        is_base_currency: true,
        created_at: "2026-04-26T00:00:00Z",
        updated_at: "2026-04-26T00:00:00Z",
      },
    ],
    total: 2,
    page: 1,
    page_size: 200,
  });
  mockedListExchangeRates.mockResolvedValue({
    items: [
      {
        id: "rate-1",
        tenant_id: "tenant-1",
        source_currency_code: "USD",
        target_currency_code: "TWD",
        effective_date: "2026-04-26",
        rate: "32.5000000000",
        rate_source: "manual",
        is_inverse: false,
        is_active: true,
        created_at: "2026-04-26T00:00:00Z",
        updated_at: "2026-04-26T00:00:00Z",
      },
    ],
    total: 1,
    page: 1,
    page_size: 200,
  });
});

describe("CurrencyMastersPanel", () => {
  it("renders currency and exchange-rate masters", async () => {
    render(<CurrencyMastersPanel />);

    expect(await screen.findByText(/USD → TWD/i)).toBeTruthy();

    expect(screen.getByLabelText("Symbol for TWD")).toBeTruthy();
    expect(screen.getAllByText("Base").length).toBeGreaterThan(0);
  });

  it("shows validation feedback for duplicate effective-dated exchange rates", async () => {
    render(<CurrencyMastersPanel />);

    await waitFor(() => {
      expect(screen.getByLabelText("New exchange rate source currency")).toBeTruthy();
    });

    fireEvent.change(screen.getByLabelText("New exchange rate source currency"), {
      target: { value: "USD" },
    });
    fireEvent.change(screen.getByLabelText("New exchange rate target currency"), {
      target: { value: "TWD" },
    });
    fireEvent.change(screen.getByLabelText("New exchange rate effective date"), {
      target: { value: "2026-04-26" },
    });
    fireEvent.change(screen.getByLabelText("New exchange rate value"), {
      target: { value: "32.55" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add rate" }));

    expect(await screen.findByText("An exchange rate already exists for this pair and effective date.")).toBeTruthy();
    expect(mockedCreateExchangeRate).not.toHaveBeenCalled();
  });
});