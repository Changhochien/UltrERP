import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CategoryCombobox } from "../../domain/inventory/components/CategoryCombobox";
import { createCategory, listCategories } from "../../lib/api/inventory";

vi.mock("../../lib/api/inventory", () => ({
  createCategory: vi.fn(),
  listCategories: vi.fn(),
}));

const CATEGORY = {
  id: "category-1",
  tenant_id: "tenant-1",
  name: "Hardware",
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
  vi.mocked(listCategories).mockResolvedValue({
    items: [CATEGORY],
    total: 1,
  });
  vi.mocked(createCategory).mockResolvedValue({
    ok: true,
    data: {
      ...CATEGORY,
      id: "category-2",
      name: "Machinery",
    },
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe("CategoryCombobox", () => {
  it("returns the selected category name", async () => {
    const onChange = vi.fn();

    render(
      <CategoryCombobox
        value=""
        onChange={onChange}
        placeholder="Filter by category"
      />,
    );

    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.click(await screen.findByText("Hardware"));

    expect(onChange).toHaveBeenCalledWith("Hardware");
  });

  it("creates a category inline and writes the new name back", async () => {
    vi.mocked(listCategories).mockResolvedValue({ items: [], total: 0 });
    const onChange = vi.fn();

    render(
      <CategoryCombobox
        value=""
        onChange={onChange}
        placeholder="Search or create category…"
        allowCreate
      />,
    );

    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.change(await screen.findByPlaceholderText("Search or create category…"), {
      target: { value: "Machinery" },
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Create category" })).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: "Create category" }));

    await waitFor(() => {
      expect(createCategory).toHaveBeenCalledWith({ name: "Machinery" });
    });
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith("Machinery");
    });
  });
});