import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";

import * as dashboardApi from "../../../lib/api/dashboard";
import { useTopCustomers } from "../hooks/useDashboard";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useTopCustomers", () => {
  it("reloads when the anchor date changes", async () => {
    const fetchTopCustomers = vi.spyOn(dashboardApi, "fetchTopCustomers").mockResolvedValue({
      period: "year",
      start_date: "2026-01-01",
      end_date: "2026-12-31",
      customers: [],
    });

    const { result } = renderHook(() => useTopCustomers("year"));

    await waitFor(() => expect(fetchTopCustomers).toHaveBeenCalledTimes(1));

    await act(async () => {
      result.current.setAnchorDate("2025-06-01");
    });

    await waitFor(() => expect(fetchTopCustomers).toHaveBeenLastCalledWith("year", "2025-06-01"));

    await act(async () => {
      result.current.setPeriod("quarter");
    });

    await waitFor(() => expect(fetchTopCustomers).toHaveBeenLastCalledWith("quarter", "2025-06-01"));
  });
});