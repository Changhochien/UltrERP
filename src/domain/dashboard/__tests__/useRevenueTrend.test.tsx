import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";

import * as dashboardApi from "../../../lib/api/dashboard";
import { useRevenueTrend } from "../hooks/useDashboard";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useRevenueTrend", () => {
  it("prepends older pages and advances the before cursor", async () => {
    const fetchRevenueTrend = vi
      .spyOn(dashboardApi, "fetchRevenueTrend")
      .mockResolvedValueOnce({
        items: [
          { date: "2025-01-01", revenue: "100", order_count: 1 },
          { date: "2025-02-01", revenue: "200", order_count: 2 },
        ],
        start_date: "2025-01-01",
        end_date: "2025-02-01",
        has_more: true,
      })
      .mockResolvedValueOnce({
        items: [
          { date: "2024-11-01", revenue: "50", order_count: 1 },
          { date: "2024-12-01", revenue: "75", order_count: 1 },
        ],
        start_date: "2024-11-01",
        end_date: "2024-12-01",
        has_more: true,
      })
      .mockResolvedValueOnce({
        items: [
          { date: "2024-09-01", revenue: "25", order_count: 1 },
          { date: "2024-10-01", revenue: "40", order_count: 1 },
        ],
        start_date: "2024-09-01",
        end_date: "2024-10-01",
        has_more: false,
      });

    const { result } = renderHook(() => useRevenueTrend("year"));

    await waitFor(() => expect(result.current.data?.items).toHaveLength(2));
    expect(fetchRevenueTrend).toHaveBeenNthCalledWith(1, "year", null);

    await act(async () => {
      await result.current.loadMore();
    });

    await waitFor(() => expect(result.current.data?.items).toHaveLength(4));
    expect(fetchRevenueTrend).toHaveBeenNthCalledWith(2, "year", "2025-01-01");
    expect(result.current.data?.items.map((item) => item.date)).toEqual([
      "2024-11-01",
      "2024-12-01",
      "2025-01-01",
      "2025-02-01",
    ]);

    await act(async () => {
      await result.current.loadMore();
    });

    await waitFor(() => expect(result.current.hasMore).toBe(false));
    expect(fetchRevenueTrend).toHaveBeenNthCalledWith(3, "year", "2024-11-01");
    expect(result.current.data?.items.map((item) => item.date)).toEqual([
      "2024-09-01",
      "2024-10-01",
      "2024-11-01",
      "2024-12-01",
      "2025-01-01",
      "2025-02-01",
    ]);
  });
});