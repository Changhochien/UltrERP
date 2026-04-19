import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { UnitsPage } from "./UnitsPage";

const mocks = vi.hoisted(() => ({
  canWrite: vi.fn(() => true),
  navigate: vi.fn(),
  createUnit: vi.fn(),
  listUnits: vi.fn(),
  setUnitStatus: vi.fn(),
  updateUnit: vi.fn(),
}));

vi.mock("react-i18next", () => ({
  useTranslation: (_ns?: string, options?: { keyPrefix?: string }) => ({
    t: (key: string, vars?: Record<string, unknown>) => {
      if (key === "units" && vars?.count != null) {
        return `${vars.count} units`;
      }
      return options?.keyPrefix ? `${options.keyPrefix}.${key}` : key;
    },
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mocks.navigate,
  };
});

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    canWrite: mocks.canWrite,
  }),
}));

vi.mock("../../lib/api/inventory", () => ({
  createUnit: (...args: unknown[]) => mocks.createUnit(...args),
  listUnits: (...args: unknown[]) => mocks.listUnits(...args),
  setUnitStatus: (...args: unknown[]) => mocks.setUnitStatus(...args),
  updateUnit: (...args: unknown[]) => mocks.updateUnit(...args),
}));

const UNIT = {
  id: "unit-1",
  tenant_id: "tenant-1",
  code: "pcs",
  name: "Pieces",
  decimal_places: 0,
  is_active: true,
  created_at: "2026-04-01T00:00:00Z",
  updated_at: "2026-04-02T00:00:00Z",
};

beforeEach(() => {
  mocks.listUnits.mockResolvedValue({
    items: [UNIT],
    total: 1,
  });
  mocks.createUnit.mockResolvedValue({
    ok: true,
    data: {
      ...UNIT,
      id: "unit-2",
      code: "box",
      name: "Box",
    },
  });
  mocks.updateUnit.mockResolvedValue({ ok: true, data: UNIT });
  mocks.setUnitStatus.mockResolvedValue({
    ok: true,
    data: {
      ...UNIT,
      is_active: false,
    },
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("UnitsPage", () => {
  it("creates a new unit from the management page", async () => {
    render(<UnitsPage />);

    fireEvent.change(screen.getByLabelText("inventory.unitsPage.codeLabel"), {
      target: { value: "box" },
    });
    fireEvent.change(screen.getByLabelText("inventory.unitsPage.nameLabel"), {
      target: { value: "Box" },
    });
    fireEvent.change(screen.getByLabelText("inventory.unitsPage.decimalPlacesLabel"), {
      target: { value: "0" },
    });
    fireEvent.click(screen.getByRole("button", { name: "inventory.unitsPage.save" }));

    await waitFor(() => {
      expect(mocks.createUnit).toHaveBeenCalledWith({
        code: "box",
        name: "Box",
        decimal_places: 0,
      });
    });
  });

  it("deactivates an existing unit from the directory", async () => {
    render(<UnitsPage />);

    expect(await screen.findByText("pcs")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "inventory.unitsPage.deactivate" }));

    await waitFor(() => {
      expect(mocks.setUnitStatus).toHaveBeenCalledWith("unit-1", false);
    });
  });
});