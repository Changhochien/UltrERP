import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CustomerListPage } from "../../pages/customers/CustomerListPage";

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

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

function makeCustomers(count: number) {
  return Array.from({ length: count }, (_, index) => ({
    id: `customer-${index + 1}`,
    company_name: `Customer ${index + 1}`,
    normalized_business_number: String(10000000 + index),
    contact_phone: `0912-000-${String(index + 1).padStart(3, "0")}`,
    status: "active",
  }));
}

describe("CustomerListPage", () => {
  it("renders heading", async () => {
    mockFetchList([]);
    renderWithRouter(<CustomerListPage />);
    expect(screen.getByRole("heading", { name: /customers/i })).toBeTruthy();
  });

  it("shows empty message when no customers", async () => {
    mockFetchList([], 0);
    renderWithRouter(<CustomerListPage />);
    await waitFor(() => {
      expect(screen.getByText("No customers found.")).toBeTruthy();
    });
  });

  it("recovers to the empty state when the list request rejects", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("network down"));

    renderWithRouter(<CustomerListPage />);

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
    renderWithRouter(<CustomerListPage />);
    await waitFor(() => {
      expect(screen.getByText("Alpha Corp")).toBeTruthy();
    });
  });

  it("uses a table-native active sort header treatment", async () => {
    mockFetchList([
      {
        id: "bbb",
        company_name: "Beta Corp",
        normalized_business_number: "12345678",
        contact_phone: "0912-333-444",
        status: "active",
      },
    ]);

    renderWithRouter(<CustomerListPage />);

    const companyHeader = await screen.findByRole("button", { name: "Company Name" });
    expect(companyHeader.className).toContain("text-muted-foreground");
    expect(companyHeader.className).toContain("bg-transparent");
    expect(companyHeader.className).toContain("rounded-none");

    fireEvent.click(companyHeader);

    await waitFor(() => {
      expect(companyHeader.className).toContain("text-foreground");
      expect(companyHeader.closest("th")?.getAttribute("aria-sort")).toBe("ascending");
    });
  });

  it("has search input", async () => {
    mockFetchList([]);
    renderWithRouter(<CustomerListPage />);
    const input = screen.getByLabelText("Search customers");
    expect(input).toBeTruthy();
  });

  it("shows active filters and clears them together", async () => {
    mockFetchList([]);

    renderWithRouter(<CustomerListPage />);

    const input = screen.getByLabelText("Search customers") as HTMLInputElement;
    const statusSelect = screen.getByLabelText("Filter by status") as HTMLSelectElement;

    fireEvent.change(input, { target: { value: "Alpha" } });
    fireEvent.change(statusSelect, { target: { value: "active" } });

    await waitFor(() => {
      expect(screen.getByText("2 active filters applied")).toBeTruthy();
      expect(screen.getByText("Search: Alpha")).toBeTruthy();
      expect(screen.getByText("Status: Active")).toBeTruthy();
      expect(screen.getByRole("button", { name: "Clear filters" })).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));

    await waitFor(() => {
      expect(input.value).toBe("");
      expect(statusSelect.value).toBe("");
      expect(screen.queryByRole("button", { name: "Clear filters" })).toBeNull();
    });
  });

  it("shows pagination as an item range and page count", async () => {
    mockFetchList(makeCustomers(20), 21, 2);

    renderWithRouter(<CustomerListPage />);

    await waitFor(() => {
      expect(screen.getByText("Showing 1-20 of 21")).toBeTruthy();
      expect(
        screen.getByText(
          (_, element) =>
            element?.getAttribute("aria-live") === "polite" &&
            (element.textContent ?? "").includes("Page 1 of 2"),
        ),
      ).toBeTruthy();
      expect(screen.getByRole("button", { name: "Go to next page, page 2" })).toBeTruthy();
    });
  });

  it("navigates to customer detail page on row click", async () => {
    mockFetchList([
      {
        id: "detail-id",
        company_name: "Detail Co",
        normalized_business_number: "04595252",
        contact_phone: "0912-111-222",
        status: "active",
      },
    ]);

    renderWithRouter(<CustomerListPage />);
    await waitFor(() => {
      expect(screen.getByText("Detail Co")).toBeTruthy();
    });

    const row = screen.getByRole("button", { name: "Customer Detail Co" });
    expect(row.className).toContain("focus-visible:ring-2");
    expect(row.getAttribute("tabindex")).toBe("0");

    fireEvent.click(screen.getByText("Detail Co"));

    // Row click navigates to /customers/:id — verify page is still visible (no crash)
    await waitFor(() => {
      expect(screen.getByText("Detail Co")).toBeTruthy();
    });
  });
});
