import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CategoriesPage } from "./CategoriesPage";

const mocks = vi.hoisted(() => ({
  canWrite: vi.fn(() => true),
  navigate: vi.fn(),
  createCategory: vi.fn(),
  listCategories: vi.fn(),
  setCategoryStatus: vi.fn(),
  updateCategory: vi.fn(),
}));

vi.mock("react-i18next", () => ({
  useTranslation: (_ns?: string, options?: { keyPrefix?: string }) => ({
    t: (key: string, vars?: Record<string, unknown>) => {
      if (key === "categories" && vars?.count != null) {
        return `${vars.count} categories`;
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
  createCategory: (...args: unknown[]) => mocks.createCategory(...args),
  listCategories: (...args: unknown[]) => mocks.listCategories(...args),
  setCategoryStatus: (...args: unknown[]) => mocks.setCategoryStatus(...args),
  updateCategory: (...args: unknown[]) => mocks.updateCategory(...args),
}));

const CATEGORY = {
  id: "category-1",
  tenant_id: "tenant-1",
  name: "Hardware",
  is_active: true,
  created_at: "2026-04-01T00:00:00Z",
  updated_at: "2026-04-02T00:00:00Z",
};

beforeEach(() => {
  mocks.listCategories.mockResolvedValue({
    items: [CATEGORY],
    total: 1,
  });
  mocks.createCategory.mockResolvedValue({
    ok: true,
    data: {
      ...CATEGORY,
      id: "category-2",
      name: "Seasonal",
    },
  });
  mocks.updateCategory.mockResolvedValue({ ok: true, data: CATEGORY });
  mocks.setCategoryStatus.mockResolvedValue({
    ok: true,
    data: {
      ...CATEGORY,
      is_active: false,
    },
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("CategoriesPage", () => {
  it("creates a new category from the management page", async () => {
    render(<CategoriesPage />);

    fireEvent.change(screen.getByLabelText("inventory.categoriesPage.nameLabel"), {
      target: { value: "Seasonal" },
    });
    fireEvent.click(screen.getByRole("button", { name: "inventory.categoriesPage.save" }));

    await waitFor(() => {
      expect(mocks.createCategory).toHaveBeenCalledWith({ name: "Seasonal" });
    });
  });

  it("deactivates an existing category from the directory", async () => {
    render(<CategoriesPage />);

    expect(await screen.findByText("Hardware")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "inventory.categoriesPage.deactivate" }));

    await waitFor(() => {
      expect(mocks.setCategoryStatus).toHaveBeenCalledWith("category-1", "inactive");
    });
  });
});