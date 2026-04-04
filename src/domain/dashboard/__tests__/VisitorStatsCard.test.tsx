import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";

import { VisitorStatsCard } from "../components/VisitorStatsCard";

function renderCard() {
  return render(<VisitorStatsCard />);
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const successResponse = {
  visitor_count: 250,
  inquiry_count: 12,
  conversion_rate: "4.8",
  date: "2026-04-01",
  is_configured: true,
  error: null,
};

describe("VisitorStatsCard", () => {
  it("renders visitor count, inquiry count, and conversion rate", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => successResponse,
    } as Response);

    renderCard();

    await waitFor(() => {
      expect(screen.getByTestId("visitor-count")).toBeTruthy();
    });

    expect(screen.getByTestId("visitor-count").textContent).toBe("250");
    expect(screen.getByTestId("inquiry-count").textContent).toBe("12");
    expect(screen.getByTestId("conversion-rate").textContent).toBe("4.8%");
    expect(screen.getByTestId("visitor-date").textContent).toContain("2026-04-01");
  });

  it("shows not-configured state", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        ...successResponse,
        is_configured: false,
        visitor_count: 0,
        inquiry_count: 0,
        conversion_rate: null,
      }),
    } as Response);

    renderCard();

    await waitFor(() => {
      expect(screen.getByTestId("visitor-not-configured")).toBeTruthy();
    });

    expect(screen.getByText("Analytics not configured")).toBeTruthy();
  });

  it("shows error state when API call fails", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));

    renderCard();

    await waitFor(() => {
      expect(screen.getByText("Analytics unavailable")).toBeTruthy();
    });
  });

  it("shows error state when backend reports PostHog error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        ...successResponse,
        error: "Analytics unavailable",
        visitor_count: 0,
        inquiry_count: 0,
        conversion_rate: null,
      }),
    } as Response);

    renderCard();

    await waitFor(() => {
      expect(screen.getByText("Analytics unavailable")).toBeTruthy();
    });
  });

  it("shows loading state", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));

    renderCard();

    expect(screen.getByTestId("visitor-stats-loading")).toBeTruthy();
  });

  it("shows dash for conversion rate when null", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        ...successResponse,
        visitor_count: 0,
        inquiry_count: 0,
        conversion_rate: null,
      }),
    } as Response);

    renderCard();

    await waitFor(() => {
      expect(screen.getByTestId("conversion-rate")).toBeTruthy();
    });

    expect(screen.getByTestId("conversion-rate").textContent).toBe("—");
  });
});
