import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const mocks = vi.hoisted(() => ({
  approvePhysicalCountSession: vi.fn(),
  fetchPhysicalCountSession: vi.fn(),
  submitPhysicalCountSession: vi.fn(),
  updatePhysicalCountLine: vi.fn(),
}));

const countSessionDetailTranslations = vi.hoisted(() => ({
  t: (key: string, vars?: Record<string, unknown>) => {
    if (key === "title" && vars?.id) {
      return `Count Session ${vars.id}`;
    }
    if (key === "countedProgress" && vars?.counted != null && vars?.total != null) {
      return `${vars.counted} / ${vars.total} lines counted`;
    }
    return `inventory.countSessionDetailPage.${key}`;
  },
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: countSessionDetailTranslations.t,
  }),
}));

vi.mock("../../lib/api/inventory", () => ({
  approvePhysicalCountSession: (...args: unknown[]) => mocks.approvePhysicalCountSession(...args),
  fetchPhysicalCountSession: (...args: unknown[]) => mocks.fetchPhysicalCountSession(...args),
  submitPhysicalCountSession: (...args: unknown[]) => mocks.submitPhysicalCountSession(...args),
  updatePhysicalCountLine: (...args: unknown[]) => mocks.updatePhysicalCountLine(...args),
}));

beforeEach(() => {
  mocks.fetchPhysicalCountSession.mockResolvedValue({
    ok: true,
    data: {
      id: "session-1",
      warehouse_id: "warehouse-1",
      warehouse_name: "Main Warehouse",
      status: "submitted",
      created_by: "user-1",
      submitted_by: "user-1",
      submitted_at: "2026-04-18T00:00:00Z",
      approved_by: null,
      approved_at: null,
      created_at: "2026-04-18T00:00:00Z",
      updated_at: "2026-04-18T00:00:00Z",
      total_lines: 1,
      counted_lines: 1,
      variance_total: -2,
      lines: [
        {
          id: "line-1",
          product_id: "product-1",
          product_code: "SKU-1",
          product_name: "Widget",
          system_qty_snapshot: 10,
          counted_qty: 8,
          variance_qty: -2,
          notes: "Recounted",
          created_at: "2026-04-18T00:00:00Z",
          updated_at: "2026-04-18T00:00:00Z",
        },
      ],
    },
  });
  mocks.submitPhysicalCountSession.mockResolvedValue({ ok: true });
  mocks.updatePhysicalCountLine.mockResolvedValue({ ok: true });
  mocks.approvePhysicalCountSession.mockResolvedValue({ ok: false, error: "Physical count snapshot is stale for Widget" });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("CountSessionDetailPage", () => {
  it("surfaces stale approval conflicts from the backend", async () => {
    const { CountSessionDetailPage } = await import("./CountSessionDetailPage");

    render(
      <MemoryRouter initialEntries={["/inventory/count-sessions/session-1"]}>
        <Routes>
          <Route path="/inventory/count-sessions/:sessionId" element={<CountSessionDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await screen.findByText("Widget");
    fireEvent.click(screen.getByRole("button", { name: "inventory.countSessionDetailPage.approve" }));

    await waitFor(() => {
      expect(mocks.approvePhysicalCountSession).toHaveBeenCalledWith("session-1");
    });
    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toContain("stale");
    });
  });

  it("rejects saving a blank counted quantity", async () => {
    mocks.fetchPhysicalCountSession.mockResolvedValue({
      ok: true,
      data: {
        id: "session-2",
        warehouse_id: "warehouse-1",
        warehouse_name: "Main Warehouse",
        status: "in_progress",
        created_by: "user-1",
        submitted_by: null,
        submitted_at: null,
        approved_by: null,
        approved_at: null,
        created_at: "2026-04-18T00:00:00Z",
        updated_at: "2026-04-18T00:00:00Z",
        total_lines: 1,
        counted_lines: 0,
        variance_total: 0,
        lines: [
          {
            id: "line-blank",
            product_id: "product-1",
            product_code: "SKU-1",
            product_name: "Widget",
            system_qty_snapshot: 10,
            counted_qty: null,
            variance_qty: null,
            notes: null,
            created_at: "2026-04-18T00:00:00Z",
            updated_at: "2026-04-18T00:00:00Z",
          },
        ],
      },
    });
    const { CountSessionDetailPage } = await import("./CountSessionDetailPage");

    render(
      <MemoryRouter initialEntries={["/inventory/count-sessions/session-2"]}>
        <Routes>
          <Route path="/inventory/count-sessions/:sessionId" element={<CountSessionDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await screen.findByText("Widget");
    const saveLineLabel = screen.getByText("inventory.countSessionDetailPage.saveLine");
    const saveLineButton = saveLineLabel.closest("button");
    if (saveLineButton == null) {
      throw new Error("Expected the save-line button to be rendered");
    }
    fireEvent.click(saveLineButton);

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toContain("invalidQuantity");
    });
    expect(mocks.updatePhysicalCountLine).not.toHaveBeenCalled();
  });
});