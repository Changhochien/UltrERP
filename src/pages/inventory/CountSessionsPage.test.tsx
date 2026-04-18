import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CountSessionsPage } from "./CountSessionsPage";

const mocks = vi.hoisted(() => ({
  createPhysicalCountSession: vi.fn(),
  fetchPhysicalCountSessions: vi.fn(),
  navigate: vi.fn(),
}));

const countSessionsTranslations = vi.hoisted(() => ({
  t: (key: string, vars?: Record<string, unknown>) => {
    if (key === "total" && vars?.count != null) {
      return `${vars.count} sessions`;
    }
    if (key === "countedProgress" && vars?.counted != null && vars?.total != null) {
      return `${vars.counted} / ${vars.total} lines counted`;
    }
    return `inventory.countSessionsPage.${key}`;
  },
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: countSessionsTranslations.t,
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mocks.navigate,
  };
});

vi.mock("../../domain/inventory/hooks/useWarehouses", () => ({
  useWarehouses: () => ({
    warehouses: [{ id: "warehouse-1", name: "Main Warehouse" }],
    loading: false,
  }),
}));

vi.mock("../../lib/api/inventory", () => ({
  createPhysicalCountSession: (...args: unknown[]) => mocks.createPhysicalCountSession(...args),
  fetchPhysicalCountSessions: (...args: unknown[]) => mocks.fetchPhysicalCountSessions(...args),
}));

beforeEach(() => {
  mocks.fetchPhysicalCountSessions.mockResolvedValue({ ok: true, data: { items: [], total: 0 } });
  mocks.createPhysicalCountSession.mockResolvedValue({ ok: true, data: { id: "session-1" } });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("CountSessionsPage", () => {
  it("starts a new physical count session and navigates to the detail route", async () => {
    render(<CountSessionsPage />);

    fireEvent.click(screen.getByRole("button", { name: "inventory.countSessionsPage.create" }));

    await waitFor(() => {
      expect(mocks.createPhysicalCountSession).toHaveBeenCalledWith({ warehouse_id: "warehouse-1" });
    });
    await waitFor(() => {
      expect(mocks.navigate).toHaveBeenCalledWith("/inventory/count-sessions/session-1");
    });
  });
});