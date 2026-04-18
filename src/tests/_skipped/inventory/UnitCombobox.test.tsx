import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { UnitCombobox } from "../../domain/inventory/components/UnitCombobox";
import { listUnits } from "../../lib/api/inventory";

vi.mock("../../lib/api/inventory", () => ({
  listUnits: vi.fn(),
}));

const UNIT = {
  id: "unit-1",
  tenant_id: "tenant-1",
  code: "pcs",
  name: "Pieces",
  decimal_places: 0,
  is_active: true,
  created_at: "2026-04-01T00:00:00Z",
  updated_at: "2026-04-01T00:00:00Z",
};

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

beforeEach(() => {
  vi.stubGlobal("ResizeObserver", ResizeObserverMock);
  vi.mocked(listUnits).mockResolvedValue({
    items: [UNIT, { ...UNIT, id: "unit-2", code: "box", name: "Box" }],
    total: 2,
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe("UnitCombobox", () => {
  it("returns the selected unit code", async () => {
    const onChange = vi.fn();

    render(
      <UnitCombobox
        value=""
        onChange={onChange}
        placeholder="Search unit…"
      />,
    );

    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.click(await screen.findByText("Box"));

    expect(onChange).toHaveBeenCalledWith("box");
  });
});