import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CustomerListPage } from "../../pages/customers/CustomerListPage";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function mockFetchList(items: object[], total_count = 1, total_pages = 1) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    json: async () => ({
      items,
      page: 1,
      page_size: 20,
      total_count,
      total_pages,
    }),
  } as Response);
}

describe("CustomerListPage", () => {
  it("renders heading", async () => {
    mockFetchList([]);
    render(<CustomerListPage />);
    expect(screen.getByText("Customers")).toBeTruthy();
  });

  it("shows empty message when no customers", async () => {
    mockFetchList([], 0);
    render(<CustomerListPage />);
    await waitFor(() => {
      expect(screen.getByText("No customers found.")).toBeTruthy();
    });
  });

  it("recovers to the empty state when the list request rejects", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("network down"));

    render(<CustomerListPage />);

    await waitFor(() => {
      expect(screen.getByText("No customers found.")).toBeTruthy();
    });
  });

  it("renders customer rows from API", async () => {
    mockFetchList([
      {
        id: "aaa",
        company_name: "Alpha Corp",
        normalized_business_number: "04595252",
        contact_phone: "0912-111-222",
        status: "active",
      },
    ]);
    render(<CustomerListPage />);
    await waitFor(() => {
      expect(screen.getByText("Alpha Corp")).toBeTruthy();
    });
  });

  it("has search input", async () => {
    mockFetchList([]);
    render(<CustomerListPage />);
    const input = screen.getByLabelText("Search customers");
    expect(input).toBeTruthy();
  });

  it("opens detail dialog on row click", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    // First call: list
    fetchSpy.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [
          {
            id: "detail-id",
            company_name: "Detail Co",
            normalized_business_number: "04595252",
            contact_phone: "0912-111-222",
            status: "active",
          },
        ],
        page: 1,
        page_size: 20,
        total_count: 1,
        total_pages: 1,
      }),
    } as Response);
    // Second call: getCustomer detail
    fetchSpy.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: "detail-id",
        tenant_id: "t",
        company_name: "Detail Co",
        normalized_business_number: "04595252",
        billing_address: "Taipei",
        contact_name: "Bob",
        contact_phone: "0912-111-222",
        contact_email: "bob@example.com",
        credit_limit: "5000",
        status: "active",
        version: 1,
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-01T00:00:00Z",
      }),
    } as Response);

    render(<CustomerListPage />);
    await waitFor(() => {
      expect(screen.getByText("Detail Co")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Detail Co"));

    await waitFor(() => {
      expect(screen.getByText("Billing Address")).toBeTruthy();
      expect(screen.getByText("Taipei")).toBeTruthy();
    });
  });
});
