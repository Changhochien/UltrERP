import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AffinityMatrix } from "../../domain/intelligence/components/AffinityMatrix";
import { fetchProductAffinityMap } from "../../lib/api/intelligence";

vi.mock("../../lib/api/intelligence", () => ({
  fetchProductAffinityMap: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("AffinityMatrix", () => {
  it("renders affinity rows sorted by score by default", async () => {
    vi.mocked(fetchProductAffinityMap).mockResolvedValue({
      pairs: [
        {
          product_a_id: "prod-a",
          product_b_id: "prod-b",
          product_a_name: "Printer Ink",
          product_b_name: "Laser Toner",
          shared_customer_count: 2,
          customer_count_a: 3,
          customer_count_b: 3,
          shared_order_count: 1,
          overlap_pct: 66.67,
          affinity_score: 0.5,
          pitch_hint: "Strong affinity",
        },
        {
          product_a_id: "prod-c",
          product_b_id: "prod-d",
          product_a_name: "Shipping Labels",
          product_b_name: "Packing Tape",
          shared_customer_count: 3,
          customer_count_a: 10,
          customer_count_b: 10,
          shared_order_count: 2,
          overlap_pct: 30,
          affinity_score: 0.1765,
          pitch_hint: "Moderate affinity",
        },
      ],
      total: 2,
      min_shared: 2,
      limit: 50,
      computed_at: "2026-04-14T01:30:00Z",
    });

    render(<AffinityMatrix />);

    expect(await screen.findByText("Product Affinity Map")).toBeTruthy();
    const rows = screen.getAllByRole("row");
    const firstDataRow = rows[1];
    expect(within(firstDataRow).getByText("Printer Ink")).toBeTruthy();
    expect(within(firstDataRow).getByText("Laser Toner")).toBeTruthy();
    expect(screen.getByText("Showing 2 of 2 pairs")).toBeTruthy();
  });

  it("resorts rows when clicking the shared customers header", async () => {
    vi.mocked(fetchProductAffinityMap).mockResolvedValue({
      pairs: [
        {
          product_a_id: "prod-a",
          product_b_id: "prod-b",
          product_a_name: "Printer Ink",
          product_b_name: "Laser Toner",
          shared_customer_count: 2,
          customer_count_a: 3,
          customer_count_b: 3,
          shared_order_count: 1,
          overlap_pct: 66.67,
          affinity_score: 0.5,
          pitch_hint: "Strong affinity",
        },
        {
          product_a_id: "prod-c",
          product_b_id: "prod-d",
          product_a_name: "Shipping Labels",
          product_b_name: "Packing Tape",
          shared_customer_count: 5,
          customer_count_a: 12,
          customer_count_b: 9,
          shared_order_count: 4,
          overlap_pct: 55.56,
          affinity_score: 0.3125,
          pitch_hint: "Higher shared customers",
        },
      ],
      total: 2,
      min_shared: 2,
      limit: 50,
      computed_at: "2026-04-14T01:30:00Z",
    });

    render(<AffinityMatrix />);

    await screen.findByText("Product Affinity Map");
    fireEvent.click(screen.getByRole("button", { name: "Sort by Shared Customers" }));

    const rows = screen.getAllByRole("row");
    const firstDataRow = rows[1];
    expect(within(firstDataRow).getByText("Shipping Labels")).toBeTruthy();
    expect(within(firstDataRow).getByText("Packing Tape")).toBeTruthy();
  });

  it("renders the empty state when no pairs qualify", async () => {
    vi.mocked(fetchProductAffinityMap).mockResolvedValue({
      pairs: [],
      total: 0,
      min_shared: 2,
      limit: 50,
      computed_at: "2026-04-14T01:30:00Z",
    });

    render(<AffinityMatrix />);

    expect(await screen.findByText("No qualifying product affinities yet.")).toBeTruthy();
  });
});