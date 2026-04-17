import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";

vi.mock("@visx/responsive", () => ({
  useParentSize: () => [{ width: 600, height: 300 }, vi.fn()],
  ParentSize: ({ children }: { children: (dims: { width: number; height: number }) => React.ReactNode }) =>
    children({ width: 600, height: 300 }),
}));

global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

import { StockTrendChart } from "../components/StockTrendChart";

vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");

  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
    LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    CartesianGrid: () => null,
    XAxis: () => null,
    YAxis: () => null,
    Tooltip: () => null,
    ReferenceLine: () => null,
    ReferenceArea: () => null,
    Line: ({ data = [], dot = false }: { data?: unknown[]; dot?: boolean | ((props: Record<string, unknown>) => React.ReactNode) }) => {
      const dots = typeof dot === "function"
        ? data.map((payload, index) => dot({ cx: index + 1, cy: index + 1, payload, key: `dot-${index}` }))
        : null;

      return <div data-testid="line">{dots}</div>;
    },
    Dot: () => <div data-testid="dot" />,
  };
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const mockPoints = [
  {
    date: "2026-04-01",
    quantity_change: -2,
    reason_code: "sales_reservation",
    running_stock: 18,
    notes: null,
  },
  {
    date: "2026-04-02",
    quantity_change: 4,
    reason_code: "supplier_delivery",
    running_stock: 22,
    notes: null,
  },
];

describe("StockTrendChart", () => {
  it("renders custom dots without emitting React key warnings", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const { container } = render(
      <StockTrendChart
        points={mockPoints}
        reorderPoint={10}
        safetyStock={5}
        avgDailyUsage={1}
      />,
    );

    expect(container.querySelector("svg")).toBeTruthy();
    expect(
      consoleErrorSpy.mock.calls.filter(
        ([message]) =>
          typeof message === "string"
          && message.includes('Each child in a list should have a unique "key" prop'),
      ),
    ).toHaveLength(0);
  });
});