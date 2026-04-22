import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CRMSetupPage from "../../pages/crm/CRMSetupPage";
import { useCRMSetupBundle } from "../../domain/crm/hooks/useCRMSetupBundle";
import { updateCRMSettings } from "../../lib/api/crm";

vi.mock("../../domain/crm/hooks/useCRMSetupBundle", () => ({
  useCRMSetupBundle: vi.fn(),
}));

vi.mock("../../lib/api/crm", () => ({
  updateCRMSettings: vi.fn(),
  createCRMSalesStage: vi.fn(),
  updateCRMSalesStage: vi.fn(),
  createCRMTerritory: vi.fn(),
  updateCRMTerritory: vi.fn(),
  createCRMCustomerGroup: vi.fn(),
  updateCRMCustomerGroup: vi.fn(),
}));

vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => ({ user: { role: "admin" } }),
}));

vi.mock("../../hooks/useToast", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const mockedUseCRMSetupBundle = vi.mocked(useCRMSetupBundle);
const mockedUpdateCRMSettings = vi.mocked(updateCRMSettings);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  mockedUseCRMSetupBundle.mockReturnValue({
    data: {
      settings: {
        lead_duplicate_policy: "block",
        default_quotation_validity_days: 30,
        contact_creation_enabled: true,
        carry_forward_communications: true,
        carry_forward_comments: true,
        opportunity_auto_close_days: 45,
      },
      sales_stages: [{ id: "stage-1", name: "Qualification", probability: 20, sort_order: 10, is_active: true }],
      territories: [{ id: "territory-1", name: "North", parent_id: null, is_group: false, sort_order: 10, is_active: true }],
      customer_groups: [{ id: "group-1", name: "Industrial", parent_id: null, is_group: false, sort_order: 10, is_active: true }],
    },
    loading: false,
    error: null,
    reload: vi.fn(),
    salesStageOptions: [{ id: "stage-1", name: "Qualification", probability: 20, sort_order: 10, is_active: true }],
    territoryOptions: [{ id: "territory-1", name: "North", parent_id: null, is_group: false, sort_order: 10, is_active: true }],
    customerGroupOptions: [{ id: "group-1", name: "Industrial", parent_id: null, is_group: false, sort_order: 10, is_active: true }],
  });
  mockedUpdateCRMSettings.mockResolvedValue({
    ok: true,
    data: {
      lead_duplicate_policy: "block",
      default_quotation_validity_days: 45,
      contact_creation_enabled: true,
      carry_forward_communications: true,
      carry_forward_comments: true,
      opportunity_auto_close_days: 45,
    },
  });
});

describe("CRMSetupPage", () => {
  it("saves CRM settings", async () => {
    render(
      <MemoryRouter>
        <CRMSetupPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Default quotation validity days"), {
      target: { value: "45" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save CRM settings" }));

    expect(mockedUpdateCRMSettings).toHaveBeenCalledWith(
      expect.objectContaining({ default_quotation_validity_days: 45 }),
    );
    expect(await screen.findByRole("heading", { level: 1, name: "CRM Setup" })).toBeTruthy();
  });
});
