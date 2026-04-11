import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { RevenueTrendChart } from "../components/RevenueTrendChart";

vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");

  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  };
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const mockData = Array.from({ length: 7 }, (_, i) => ({
  date: `2026-04-0${i + 1}`,
  revenue: String((i + 1) * 1000),
}));

describe("RevenueTrendChart", () => {
  it("renders loading skeleton", () => {
    render(<RevenueTrendChart data={[]} isLoading={true} error={null} onRetry={vi.fn()} period="month" onPeriodChange={vi.fn()} />);
    expect(document.querySelector(".animate-pulse")).toBeTruthy();
  });

  it("renders error state with retry button", () => {
    const onRetry = vi.fn();
    render(<RevenueTrendChart data={[]} isLoading={false} error="Network error" onRetry={onRetry} period="month" onPeriodChange={vi.fn()} />);
    expect(screen.getByText("Network error")).toBeTruthy();
    const retryBtn = screen.getByRole("button", { name: /retry/i });
    expect(retryBtn).toBeTruthy();
  });

  it("retry button triggers onRetry callback", () => {
    const onRetry = vi.fn();
    render(<RevenueTrendChart data={[]} isLoading={false} error="Network error" onRetry={onRetry} period="month" onPeriodChange={vi.fn()} />);
    screen.getByRole("button", { name: /retry/i }).click();
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("renders chart container with recharts when data is provided", () => {
    render(<RevenueTrendChart data={mockData} isLoading={false} error={null} onRetry={vi.fn()} period="month" onPeriodChange={vi.fn()} />);
    expect(screen.getByTestId("responsive-container")).toBeTruthy();
  });
});
