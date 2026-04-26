import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

const dataTableMock = vi.hoisted(() => ({
  auditSortChange: undefined as ((next: { columnId: string; direction: "asc" | "desc" } | null) => void) | undefined,
}));

const fetchUsersMock = vi.hoisted(() => vi.fn());
const fetchAuditLogsMock = vi.hoisted(() => vi.fn());
const fetchLegacyRefreshLanesMock = vi.hoisted(() => vi.fn());
const fetchLegacyRefreshRecentRunsMock = vi.hoisted(() => vi.fn());
const fetchSalesMonthlyHealthMock = vi.hoisted(() => vi.fn());
const repairSalesMonthlyMissingMock = vi.hoisted(() => vi.fn());
const backfillSalesMonthlyMock = vi.hoisted(() => vi.fn());
const translationMock = vi.hoisted(() => ({
  t: (key: string) => key,
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => translationMock,
}));

vi.mock("../components/layout/DataTable", () => ({
  DataTable: ({ sortState, onSortChange }: { sortState?: unknown; onSortChange?: (next: { columnId: string; direction: "asc" | "desc" } | null) => void }) => {
    if (sortState !== undefined) {
      dataTableMock.auditSortChange = onSortChange;
    }
    return <div>data-table</div>;
  },
}));

vi.mock("../lib/api/admin", async () => {
  const actual = await vi.importActual<typeof import("../lib/api/admin")>("../lib/api/admin");
  return {
    ...actual,
    fetchUsers: (...args: Parameters<typeof fetchUsersMock>) => fetchUsersMock(...args),
    fetchAuditLogs: (...args: Parameters<typeof fetchAuditLogsMock>) => fetchAuditLogsMock(...args),
    fetchLegacyRefreshLanes: (...args: Parameters<typeof fetchLegacyRefreshLanesMock>) =>
      fetchLegacyRefreshLanesMock(...args),
    fetchLegacyRefreshRecentRuns: (...args: Parameters<typeof fetchLegacyRefreshRecentRunsMock>) =>
      fetchLegacyRefreshRecentRunsMock(...args),
    fetchSalesMonthlyHealth: (...args: Parameters<typeof fetchSalesMonthlyHealthMock>) =>
      fetchSalesMonthlyHealthMock(...args),
    repairSalesMonthlyMissing: (...args: Parameters<typeof repairSalesMonthlyMissingMock>) =>
      repairSalesMonthlyMissingMock(...args),
    backfillSalesMonthly: (...args: Parameters<typeof backfillSalesMonthlyMock>) =>
      backfillSalesMonthlyMock(...args),
  };
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  dataTableMock.auditSortChange = undefined;
});

describe("AdminPage audit sorting", () => {
  it("omits audit sort params when the table clears sorting", async () => {
    fetchUsersMock.mockResolvedValue([]);
    fetchAuditLogsMock.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });
    fetchLegacyRefreshLanesMock.mockResolvedValue({ lanes: [] });
    fetchLegacyRefreshRecentRunsMock.mockResolvedValue([]);
    fetchSalesMonthlyHealthMock.mockResolvedValue({
      window_start: "2026-03-01",
      window_end: "2026-03-01",
      is_healthy: false,
      missing_month_count: 1,
      missing_months: [
        {
          month_start: "2026-03-01",
          transactional_order_count: 2,
          transactional_revenue: "180.00",
        },
      ],
      checked_month_count: 1,
      current_open_month: "2026-04-01",
      data_gap_acknowledged: true,
    });
    repairSalesMonthlyMissingMock.mockResolvedValue({
      repaired_months: ["2026-03-01"],
      refreshed_month_count: 1,
      results: [],
      idempotent: true,
    });

    const { AdminPage } = await import("./AdminPage");

    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(fetchAuditLogsMock).toHaveBeenCalledTimes(1);
      expect(dataTableMock.auditSortChange).toBeTruthy();
    });

    expect(fetchAuditLogsMock.mock.calls[0]?.[0]).toMatchObject({
      sort_by: "created_at",
      sort_direction: "desc",
    });

    await act(async () => {
      dataTableMock.auditSortChange?.(null);
    });

    await waitFor(() => {
      expect(fetchAuditLogsMock).toHaveBeenCalledTimes(2);
    });

    expect(fetchAuditLogsMock.mock.calls[1]?.[0]).toMatchObject({
      page: 1,
      page_size: 20,
    });
    expect(fetchAuditLogsMock.mock.calls[1]?.[0]?.sort_by).toBeUndefined();
    expect(fetchAuditLogsMock.mock.calls[1]?.[0]?.sort_direction).toBeUndefined();
  });

  it("renders legacy refresh scope diagnostics from the lane payload", async () => {
    fetchUsersMock.mockResolvedValue([]);
    fetchAuditLogsMock.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });
    fetchLegacyRefreshLanesMock.mockResolvedValue({
      lanes: [
        {
          lane_key: "raw_legacy:tenant-1:public",
          tenant_id: "tenant-1",
          schema_name: "raw_legacy",
          source_schema: "public",
          lane_locked: false,
          current_job_id: null,
          lock_acquired_at: null,
          latest_run: {
            batch_id: "legacy-incremental-001",
            summary_path: "/tmp/legacy-incremental-001-summary.json",
            started_at: "2026-04-24T01:00:00+00:00",
            completed_at: "2026-04-24T01:02:00+00:00",
            final_disposition: "completed",
            exit_code: 0,
            validation_status: "passed",
            blocking_issue_count: 0,
            reconciliation_gap_count: 0,
            promotion_policy: { classification: "eligible" },
          },
          latest_success: null,
          latest_promoted: null,
          current_batch_mode: "incremental",
          promotion_eligible: true,
          promotion_classification: "eligible",
          affected_domains: ["sales", "products"],
          root_failure: "verify_reconciliation: Targeted reconciliation exceeded threshold",
          blocked_reason: "Incremental reconciliation drift requires full rebaseline",
          incremental_state_path: "/tmp/incremental-state.json",
          nightly_rebaseline_path: null,
          summary_root: "/tmp",
        },
      ],
    });
    fetchLegacyRefreshRecentRunsMock.mockResolvedValue([]);

    const { AdminPage } = await import("./AdminPage");

    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(fetchLegacyRefreshLanesMock).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByText("sales, products")).toBeTruthy();
    expect(screen.getByText("/tmp/legacy-incremental-001-summary.json")).toBeTruthy();
    expect(screen.getByText("/tmp/incremental-state.json")).toBeTruthy();
    expect(
      screen.getByText((text) => text.includes("Incremental reconciliation drift requires full rebaseline")),
    ).toBeTruthy();

    fireEvent.change(
      screen.getByLabelText("adminPage.legacyRefresh.salesMonthly.fields.tenantId"),
      { target: { value: "tenant-1" } },
    );

    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: "adminPage.legacyRefresh.salesMonthly.actions.checkHealth" }),
      );
    });

    await waitFor(() => {
      expect(fetchSalesMonthlyHealthMock).toHaveBeenCalledWith(
        "tenant-1",
        expect.any(String),
        expect.any(String),
      );
    });

    expect(screen.getByText("2026-03-01")).toBeTruthy();

    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: "adminPage.legacyRefresh.salesMonthly.actions.repairMissing" }),
      );
    });

    await waitFor(() => {
      expect(repairSalesMonthlyMissingMock).toHaveBeenCalledWith("tenant-1", ["2026-03-01"]);
    });
  });

  it("triggers bounded sales-monthly backfill from the admin controls", async () => {
    fetchUsersMock.mockResolvedValue([]);
    fetchAuditLogsMock.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });
    fetchLegacyRefreshLanesMock.mockResolvedValue({ lanes: [] });
    fetchLegacyRefreshRecentRunsMock.mockResolvedValue([]);
    backfillSalesMonthlyMock.mockResolvedValue({
      start_month: "2026-03-01",
      end_month: "2026-03-01",
      refreshed_month_count: 1,
      results: [],
      bounded: true,
    });
    fetchSalesMonthlyHealthMock.mockResolvedValue({
      window_start: "2026-03-01",
      window_end: "2026-03-01",
      is_healthy: true,
      missing_month_count: 0,
      missing_months: [],
      checked_month_count: 1,
      current_open_month: "2026-04-01",
      data_gap_acknowledged: false,
    });

    const { AdminPage } = await import("./AdminPage");

    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(fetchLegacyRefreshLanesMock).toHaveBeenCalledTimes(1);
    });

    fireEvent.change(
      screen.getByLabelText("adminPage.legacyRefresh.salesMonthly.fields.tenantId"),
      { target: { value: "tenant-1" } },
    );

    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: "adminPage.legacyRefresh.salesMonthly.actions.backfill" }),
      );
    });

    await waitFor(() => {
      expect(backfillSalesMonthlyMock).toHaveBeenCalledWith(
        "tenant-1",
        expect.any(String),
        expect.any(String),
      );
    });
  });

  it("renders a healthy sales-monthly state and keeps repair disabled when no gaps exist", async () => {
    fetchUsersMock.mockResolvedValue([]);
    fetchAuditLogsMock.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });
    fetchLegacyRefreshLanesMock.mockResolvedValue({ lanes: [] });
    fetchLegacyRefreshRecentRunsMock.mockResolvedValue([]);
    fetchSalesMonthlyHealthMock.mockResolvedValue({
      window_start: "2026-03-01",
      window_end: "2026-03-01",
      is_healthy: true,
      missing_month_count: 0,
      missing_months: [],
      checked_month_count: 1,
      current_open_month: "2026-04-01",
      data_gap_acknowledged: false,
    });

    const { AdminPage } = await import("./AdminPage");

    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(fetchLegacyRefreshLanesMock).toHaveBeenCalledTimes(1);
    });

    const repairButton = screen.getByRole("button", {
      name: "adminPage.legacyRefresh.salesMonthly.actions.repairMissing",
    }) as HTMLButtonElement;
    expect(repairButton.disabled).toBe(true);

    fireEvent.change(
      screen.getByLabelText("adminPage.legacyRefresh.salesMonthly.fields.tenantId"),
      { target: { value: "tenant-1" } },
    );

    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: "adminPage.legacyRefresh.salesMonthly.actions.checkHealth" }),
      );
    });

    await waitFor(() => {
      expect(fetchSalesMonthlyHealthMock).toHaveBeenCalledWith(
        "tenant-1",
        expect.any(String),
        expect.any(String),
      );
    });

    expect(screen.getByText("adminPage.legacyRefresh.salesMonthly.status.healthy")).toBeTruthy();
    expect(screen.getByText("adminPage.legacyRefresh.salesMonthly.empty")).toBeTruthy();
    expect(repairButton.disabled).toBe(true);
  });
});