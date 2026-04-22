import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CRMPipelineReportPage from "../../pages/crm/CRMPipelineReportPage";
import { useCRMSetupBundle } from "../../domain/crm/hooks/useCRMSetupBundle";
import { getCRMPipelineReport } from "../../lib/api/crm";

vi.mock("../../domain/crm/hooks/useCRMSetupBundle", () => ({
  useCRMSetupBundle: vi.fn(),
}));

vi.mock("../../lib/api/crm", () => ({
  getCRMPipelineReport: vi.fn(),
}));

const mockedUseCRMSetupBundle = vi.mocked(useCRMSetupBundle);
const mockedGetCRMPipelineReport = vi.mocked(getCRMPipelineReport);

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
  mockedGetCRMPipelineReport.mockResolvedValue({
    filters: {
      record_type: "all",
      scope: "open",
      status: "",
      sales_stage: "",
      territory: "",
      customer_group: "",
      owner: "",
      lost_reason: "",
      utm_source: "",
      utm_medium: "",
      utm_campaign: "",
      utm_content: "",
    },
    totals: {
      lead_count: 3,
      opportunity_count: 4,
      quotation_count: 3,
      open_count: 7,
      terminal_count: 3,
      open_pipeline_amount: "60000.00",
      terminal_pipeline_amount: "40000.00",
      ordered_revenue: "1050.00",
      conversion_count: 2,
      avg_days_to_conversion: "4.50",
    },
    by_status: [
      {
        key: "status:open",
        label: "open",
        record_type: "opportunity",
        count: 4,
        amount: "60000.00",
      },
    ],
    by_sales_stage: [],
    by_territory: [],
    by_customer_group: [],
    by_owner: [],
    by_lost_reason: [],
    by_utm_source: [{ key: "expo", label: "expo", record_type: "order", count: 1, amount: "1050.00", ordered_revenue: "1050.00" }],
    by_utm_medium: [{ key: "field", label: "field", record_type: "order", count: 1, amount: "1050.00", ordered_revenue: "1050.00" }],
    by_utm_campaign: [{ key: "spring-2026", label: "spring-2026", record_type: "order", count: 1, amount: "1050.00", ordered_revenue: "1050.00" }],
    by_utm_content: [{ key: "hero-banner", label: "hero-banner", record_type: "order", count: 1, amount: "1050.00", ordered_revenue: "1050.00" }],
    by_conversion_path: [
      { key: "customer+opportunity", label: "customer+opportunity", record_type: "lead", count: 2, amount: "0.00" },
    ],
    by_conversion_source: [
      { key: "trade-show", label: "trade-show", record_type: "lead", count: 2, amount: "0.00" },
    ],
    dropoff: {
      lead_only_count: 2,
      opportunity_without_quotation_count: 1,
      quotation_without_order_count: 1,
      quotation_with_order_count: 2,
    },
  });
});

describe("CRMPipelineReportPage", () => {
  it("loads attribution reporting and refetches when UTM filters change", async () => {
    render(
      <MemoryRouter>
        <CRMPipelineReportPage />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { level: 1, name: "Pipeline Reporting" })).toBeTruthy();
    expect((await screen.findAllByText("60000.00")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Ordered Revenue").length).toBeGreaterThan(0);
    expect(screen.getByText("By UTM Medium")).toBeTruthy();
    expect(screen.getByText("By UTM Campaign")).toBeTruthy();
    expect(screen.getByText("By UTM Content")).toBeTruthy();
    expect(screen.getAllByText("Converted Leads").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Avg Days to Conversion").length).toBeGreaterThan(0);
    expect(screen.getByText("By Conversion Path")).toBeTruthy();
    expect(screen.getByText("By Conversion Source")).toBeTruthy();
    expect(screen.getByText("customer+opportunity")).toBeTruthy();
    expect(screen.getByText("trade-show")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("UTM Medium"), {
      target: { value: "field" },
    });

    await waitFor(() => {
      expect(mockedGetCRMPipelineReport).toHaveBeenLastCalledWith(
        expect.objectContaining({ utm_medium: "field" }),
      );
    });

    fireEvent.change(screen.getByLabelText("Record Type"), {
      target: { value: "opportunity" },
    });

    await waitFor(() => {
      expect(mockedGetCRMPipelineReport).toHaveBeenLastCalledWith(
        expect.objectContaining({ record_type: "opportunity" }),
      );
    });

    expect(screen.getAllByText("Ordered Revenue").length).toBeGreaterThan(0);
  });
});
