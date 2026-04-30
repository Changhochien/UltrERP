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
const fetchLegacyRefreshJobStatusMock = vi.hoisted(() => vi.fn());
const triggerLegacyRefreshMock = vi.hoisted(() => vi.fn());
const fetchSalesMonthlyHealthMock = vi.hoisted(() => vi.fn());
const repairSalesMonthlyMissingMock = vi.hoisted(() => vi.fn());
const backfillSalesMonthlyMock = vi.hoisted(() => vi.fn());
const optionalAuthMock = vi.hoisted(() => vi.fn<() => unknown>(() => null));
const translationMock = vi.hoisted(() => ({
  t: (key: string) => key,
}));
const originalWindowConfirm = window.confirm;

vi.mock("react-i18next", () => ({
  useTranslation: () => translationMock,
}));

vi.mock("../hooks/useAuth", async () => {
  const actual = await vi.importActual<typeof import("../hooks/useAuth")>("../hooks/useAuth");
  return {
    ...actual,
    useOptionalAuth: () => optionalAuthMock(),
  };
});

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
    fetchLegacyRefreshJobStatus: (...args: Parameters<typeof fetchLegacyRefreshJobStatusMock>) =>
      fetchLegacyRefreshJobStatusMock(...args),
    triggerLegacyRefresh: (...args: Parameters<typeof triggerLegacyRefreshMock>) =>
      triggerLegacyRefreshMock(...args),
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
  window.confirm = originalWindowConfirm;
  vi.clearAllMocks();
  optionalAuthMock.mockReturnValue(null);
  dataTableMock.auditSortChange = undefined;
  window.localStorage.clear();
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
    fetchLegacyRefreshJobStatusMock.mockResolvedValue({
      job_id: "job-1",
      batch_id: "legacy-incremental-001",
      mode: "incremental",
      status: "running",
    });
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
      expect(fetchLegacyRefreshLanesMock).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByText("sales, products")).toBeTruthy();
    expect(screen.getByText("/tmp/legacy-incremental-001-summary.json")).toBeTruthy();
    expect(screen.getByText("/tmp/incremental-state.json")).toBeTruthy();
    expect(
      screen.getByText((text) => text.includes("Incremental reconciliation drift requires full rebaseline")),
    ).toBeTruthy();

    fireEvent.change(document.getElementById("lsm-tenant-id") as HTMLInputElement, {
      target: { value: "tenant-1" },
    });

    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: /salesMonthly\.actions\.checkHealth|Check Health/i }),
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
        screen.getByRole("button", { name: /salesMonthly\.actions\.repairMissing|Repair Missing/i }),
      );
    });

    await waitFor(() => {
      expect(repairSalesMonthlyMissingMock).toHaveBeenCalledWith("tenant-1", ["2026-03-01"]);
    });
  });

  it("selects the most recent lane and launches the full quick action with the full lookback default", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);

    fetchUsersMock.mockResolvedValue([]);
    fetchAuditLogsMock.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });
    fetchLegacyRefreshLanesMock
      .mockResolvedValueOnce({
        lanes: [
          {
            lane_key: "raw_legacy:tenant-older:public",
            tenant_id: "tenant-older",
            schema_name: "raw_legacy",
            source_schema: "public",
            lane_locked: false,
            current_job_id: null,
            lock_acquired_at: null,
            latest_run: {
              batch_id: "legacy-incremental-older",
              summary_path: "/tmp/older-summary.json",
              started_at: "2026-04-23T01:00:00+00:00",
              completed_at: "2026-04-23T01:02:00+00:00",
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
            affected_domains: [],
            root_failure: null,
            blocked_reason: null,
            incremental_state_path: "/tmp/older-state.json",
            nightly_rebaseline_path: null,
            summary_root: "/tmp",
          },
          {
            lane_key: "raw_legacy:tenant-newer:public",
            tenant_id: "tenant-newer",
            schema_name: "raw_legacy",
            source_schema: "public",
            lane_locked: false,
            current_job_id: null,
            lock_acquired_at: null,
            latest_run: {
              batch_id: "legacy-incremental-newer",
              summary_path: "/tmp/newer-summary.json",
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
            affected_domains: [],
            root_failure: null,
            blocked_reason: null,
            incremental_state_path: "/tmp/newer-state.json",
            nightly_rebaseline_path: null,
            summary_root: "/tmp",
          },
        ],
      })
      .mockResolvedValueOnce({
        lanes: [
          {
            lane_key: "raw_legacy:tenant-newer:public",
            tenant_id: "tenant-newer",
            schema_name: "raw_legacy",
            source_schema: "public",
            lane_locked: false,
            current_job_id: null,
            lock_acquired_at: null,
            latest_run: {
              batch_id: "legacy-shadow-20260424T010000Z",
              summary_path: "/tmp/full-summary.json",
              started_at: "2026-04-24T01:00:00+00:00",
              completed_at: "2026-04-24T01:05:00+00:00",
              final_disposition: "completed",
              exit_code: 0,
              validation_status: "passed",
              blocking_issue_count: 0,
              reconciliation_gap_count: 0,
              promotion_policy: { classification: "eligible" },
            },
            latest_success: null,
            latest_promoted: null,
            current_batch_mode: "full-rebaseline",
            promotion_eligible: true,
            promotion_classification: "eligible",
            affected_domains: ["sales", "inventory"],
            root_failure: null,
            blocked_reason: null,
            incremental_state_path: "/tmp/newer-state.json",
            nightly_rebaseline_path: "/tmp/nightly.json",
            summary_root: "/tmp",
          },
        ],
      });
    fetchLegacyRefreshRecentRunsMock
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          job_id: "job-1",
          batch_id: "legacy-shadow-20260424T010000Z",
          mode: "full-rebaseline",
          started_at: "2026-04-24T01:00:00+00:00",
          completed_at: "2026-04-24T01:05:00+00:00",
          final_disposition: "completed",
          validation_status: "passed",
          promotion_eligible: true,
          blocked: false,
          blocked_reason: null,
        },
      ]);
    fetchLegacyRefreshJobStatusMock.mockResolvedValue({
      job_id: "job-1",
      batch_id: "legacy-shadow-20260424T010000Z",
      mode: "full-rebaseline",
      status: "completed",
      final_disposition: "completed",
      completed_at: "2026-04-24T01:05:00+00:00",
      summary_path: "/tmp/full-summary.json",
      promotion_eligible: true,
    });
    triggerLegacyRefreshMock.mockResolvedValue({
      job_id: "job-1",
      lane_key: "raw_legacy:tenant-newer:public",
      mode: "full-rebaseline",
      batch_id: "legacy-shadow-20260424T010000Z",
      launched_at: "2026-04-24T01:00:00+00:00",
      status: "queued",
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

    const laneSelect = document.getElementById("lr-lane-select") as HTMLSelectElement;
    expect(laneSelect.value).toBe("raw_legacy:tenant-newer:public");

    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: /quickActions\.fullRebaseline|Run Full Rebaseline/i }),
      );
    });

    await waitFor(() => {
      expect(triggerLegacyRefreshMock).toHaveBeenCalledWith({
        tenant_id: "tenant-newer",
        schema_name: "raw_legacy",
        source_schema: "public",
        mode: "full-rebaseline",
        dry_run: false,
        lookback_days: 10000,
        reconciliation_threshold: 0,
      });
    });

    fireEvent.click(
      screen.getByRole("button", { name: /quickActions\.showAdvanced|Advanced Settings/i }),
    );

    expect((document.getElementById("lr-tenant-id") as HTMLInputElement).value).toBe("tenant-newer");
    expect((document.getElementById("lr-schema-name") as HTMLInputElement).value).toBe("raw_legacy");
    expect(screen.getByText("legacyRefresh.monitor.succeeded")).toBeTruthy();
    expect(screen.getAllByText("/tmp/full-summary.json").length).toBeGreaterThan(0);
  });

  it("uses direct job polling to mark an active refresh as running before lane history updates", async () => {
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
          latest_run: null,
          latest_success: null,
          latest_promoted: null,
          current_batch_mode: null,
          promotion_eligible: false,
          promotion_classification: null,
          affected_domains: [],
          root_failure: null,
          blocked_reason: null,
          incremental_state_path: "/tmp/incremental-state.json",
          nightly_rebaseline_path: null,
          summary_root: "/tmp",
        },
      ],
    });
    fetchLegacyRefreshRecentRunsMock.mockResolvedValue([]);
    fetchLegacyRefreshJobStatusMock.mockResolvedValue({
      job_id: "job-running-1",
      batch_id: "legacy-incremental-20260428T010000Z",
      mode: "incremental",
      status: "running",
    });
    triggerLegacyRefreshMock.mockResolvedValue({
      job_id: "job-running-1",
      lane_key: "raw_legacy:tenant-1:public",
      mode: "incremental",
      batch_id: "legacy-incremental-20260428T010000Z",
      launched_at: "2026-04-28T01:00:00+00:00",
      status: "queued",
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

    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: /quickActions\.incremental|Run Incremental Refresh/i }),
      );
    });

    await waitFor(() => {
      expect(fetchLegacyRefreshJobStatusMock).toHaveBeenCalledWith("job-running-1");
    });

    expect(screen.getByText("legacyRefresh.monitor.running")).toBeTruthy();
  });

  it("prefills the first-run legacy refresh scope from auth and steers bootstrap lanes to full rebaseline", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);

    optionalAuthMock.mockReturnValue({
      user: {
        sub: "admin@example.com",
        role: "admin",
        tenant_id: "00000000-0000-0000-0000-000000000001",
      },
      token: "token",
      isAuthenticated: true,
      isAuthLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
    fetchUsersMock.mockResolvedValue([]);
    fetchAuditLogsMock.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });
    fetchLegacyRefreshLanesMock.mockResolvedValue({ lanes: [] });
    fetchLegacyRefreshRecentRunsMock.mockResolvedValue([]);
    fetchLegacyRefreshJobStatusMock.mockResolvedValue({
      job_id: "job-auth-1",
      batch_id: "legacy-incremental-20260428T010000Z",
      mode: "incremental",
      status: "queued",
    });
    triggerLegacyRefreshMock.mockResolvedValue({
      job_id: "job-auth-1",
      lane_key: "raw_legacy:00000000-0000-0000-0000-000000000001:public",
      mode: "incremental",
      batch_id: "legacy-incremental-20260428T010000Z",
      launched_at: "2026-04-28T01:00:00+00:00",
      status: "queued",
    });

    const { AdminPage } = await import("./AdminPage");

    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(fetchLegacyRefreshLanesMock).toHaveBeenCalledTimes(1);
      expect((document.getElementById("lr-tenant-id") as HTMLInputElement).value).toBe(
        "00000000-0000-0000-0000-000000000001",
      );
    });

    expect((document.getElementById("lr-schema-name") as HTMLInputElement).value).toBe("raw_legacy");
    expect((document.getElementById("lsm-tenant-id") as HTMLInputElement).value).toBe(
      "00000000-0000-0000-0000-000000000001",
    );
    expect(screen.queryByRole("button", { name: /quickActions\.showAdvanced|Advanced Settings/i })).toBeNull();
    expect(screen.getByText("legacyRefresh.quickActions.advancedRequired")).toBeTruthy();
    expect(screen.getByText("legacyRefresh.trigger.bootstrapRequired")).toBeTruthy();
    expect((document.getElementById("lr-mode") as HTMLSelectElement).value).toBe("full-rebaseline");
    expect(
      (screen.getByRole("button", { name: /quickActions\.incremental|Run Incremental Refresh/i }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);

    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: /quickActions\.fullRebaseline|Run Full Rebaseline/i }),
      );
    });

    await waitFor(() => {
      expect(triggerLegacyRefreshMock).toHaveBeenCalledWith({
        tenant_id: "00000000-0000-0000-0000-000000000001",
        schema_name: "raw_legacy",
        source_schema: "public",
        mode: "full-rebaseline",
        dry_run: false,
        lookback_days: 10000,
        reconciliation_threshold: 0,
      });
    });
  });

  it("shows a settings-guided warning when legacy source settings are missing", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);

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
          latest_run: null,
          latest_success: null,
          latest_promoted: null,
          current_batch_mode: "full-rebaseline",
          promotion_eligible: false,
          promotion_classification: null,
          affected_domains: [],
          root_failure: null,
          blocked_reason: null,
          incremental_state_path: "/tmp/state.json",
          nightly_rebaseline_path: null,
          summary_root: "/tmp",
        },
      ],
    });
    fetchLegacyRefreshRecentRunsMock.mockResolvedValue([]);
    triggerLegacyRefreshMock.mockResolvedValue({
      lane_key: "raw_legacy:tenant-1:public",
      conflict: "legacy-source-settings-missing",
      detail: "Missing legacy source settings: LEGACY_DB_HOST, LEGACY_DB_USER",
      existing_lock: null,
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

    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: /quickActions\.fullRebaseline|Run Full Rebaseline/i }),
      );
    });

    expect(screen.getByText("legacyRefresh.trigger.missingLegacySourceSettingsTitle")).toBeTruthy();
    expect(screen.getByText("legacyRefresh.trigger.missingLegacySourceSettingsBody")).toBeTruthy();
    expect(screen.getByText("LEGACY_DB_HOST, LEGACY_DB_USER")).toBeTruthy();
    expect(screen.getAllByRole("link", { name: /settingsHub\.openSettings|Open Settings/i }).length).toBeGreaterThan(0);
  });

  it("does not launch a full rebaseline when confirmation is rejected", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);

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
          latest_run: null,
          latest_success: null,
          latest_promoted: null,
          current_batch_mode: "full-rebaseline",
          promotion_eligible: false,
          promotion_classification: null,
          affected_domains: [],
          root_failure: null,
          blocked_reason: null,
          incremental_state_path: "/tmp/state.json",
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

    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: /quickActions\.fullRebaseline|Run Full Rebaseline/i }),
      );
    });

    expect(window.confirm).toHaveBeenCalledWith("legacyRefresh.trigger.confirmFullRebaseline");
    expect(triggerLegacyRefreshMock).not.toHaveBeenCalled();
  });

  it("restores the active refresh monitor after reload and shows richer completion metrics", async () => {
    window.localStorage.setItem(
      "ultrerp_legacy_refresh_active_job",
      JSON.stringify({
        jobId: "job-restored-1",
        batchId: "legacy-shadow-20260428T020000Z",
        laneKey: "raw_legacy:tenant-restored:public",
        mode: "full-rebaseline",
        launchedAt: "2026-04-28T02:00:00+00:00",
      }),
    );
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
          lane_key: "raw_legacy:tenant-restored:public",
          tenant_id: "tenant-restored",
          schema_name: "raw_legacy",
          source_schema: "public",
          lane_locked: false,
          current_job_id: null,
          lock_acquired_at: null,
          latest_run: null,
          latest_success: null,
          latest_promoted: null,
          current_batch_mode: "full-rebaseline",
          promotion_eligible: true,
          promotion_classification: "eligible",
          affected_domains: [],
          root_failure: null,
          blocked_reason: null,
          incremental_state_path: "/tmp/restored-state.json",
          nightly_rebaseline_path: null,
          summary_root: "/tmp",
        },
      ],
    });
    fetchLegacyRefreshRecentRunsMock.mockResolvedValue([]);
    fetchLegacyRefreshJobStatusMock.mockResolvedValue({
      job_id: "job-restored-1",
      batch_id: "legacy-shadow-20260428T020000Z",
      mode: "full-rebaseline",
      status: "completed",
      final_disposition: "completed",
      completed_at: "2026-04-28T02:05:00+00:00",
      validation_status: "passed",
      blocking_issue_count: 987,
      reconciliation_gap_count: 654,
      summary_path: "/tmp/restored-summary.json",
      promotion_eligible: true,
    });

    const { AdminPage } = await import("./AdminPage");

    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(fetchLegacyRefreshJobStatusMock).toHaveBeenCalledWith("job-restored-1");
    });

    expect(screen.getByText("legacyRefresh.monitor.succeeded")).toBeTruthy();
    expect(screen.getByText("passed")).toBeTruthy();
    expect(screen.getByText("987")).toBeTruthy();
    expect(screen.getByText("654")).toBeTruthy();
    expect(screen.getByText("/tmp/restored-summary.json")).toBeTruthy();
  });

  it("clears a stored failed refresh monitor when a newer lane success exists", async () => {
    window.localStorage.setItem(
      "ultrerp_legacy_refresh_active_job",
      JSON.stringify({
        jobId: "job-stale-failed",
        batchId: "legacy-shadow-20260429T041104Z",
        laneKey: "raw_legacy:00000000-0000-0000-0000-000000000001:public",
        mode: "full-rebaseline",
        launchedAt: "2026-04-29T04:11:04+00:00",
      }),
    );
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
          lane_key: "raw_legacy:00000000-0000-0000-0000-000000000001:public",
          tenant_id: "00000000-0000-0000-0000-000000000001",
          schema_name: "raw_legacy",
          source_schema: "public",
          lane_locked: false,
          current_job_id: null,
          lock_acquired_at: null,
          latest_run: {
            batch_id: "legacy-shadow-20260430T065740Z",
            summary_path: "/tmp/current-summary.json",
            started_at: "2026-04-30T06:57:40+00:00",
            completed_at: "2026-04-30T07:38:59+00:00",
            final_disposition: "completed",
            exit_code: 0,
            validation_status: "clean",
            blocking_issue_count: 0,
            reconciliation_gap_count: 0,
            promotion_policy: { classification: "eligible" },
          },
          latest_success: {
            batch_id: "legacy-shadow-20260430T065740Z",
            summary_path: "/tmp/current-summary.json",
            started_at: "2026-04-30T06:57:40+00:00",
            completed_at: "2026-04-30T07:38:59+00:00",
            final_disposition: "completed",
            exit_code: 0,
            validation_status: "clean",
            blocking_issue_count: 0,
            reconciliation_gap_count: 0,
            promotion_policy: { classification: "eligible" },
          },
          latest_promoted: null,
          current_batch_mode: "full-rebaseline",
          promotion_eligible: true,
          promotion_classification: "eligible",
          affected_domains: [],
          root_failure: null,
          blocked_reason: null,
          incremental_state_path: "/tmp/incremental-state.json",
          nightly_rebaseline_path: null,
          summary_root: "/tmp",
        },
      ],
    });
    fetchLegacyRefreshRecentRunsMock.mockResolvedValue([]);
    fetchLegacyRefreshJobStatusMock.mockResolvedValue({
      job_id: "job-stale-failed",
      batch_id: "legacy-shadow-20260429T041104Z",
      mode: "full-rebaseline",
      status: "completed",
      final_disposition: "failed",
      root_failure: "canonical-import: connection has been released back to the pool",
    });

    const { AdminPage } = await import("./AdminPage");

    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getAllByText("legacy-shadow-20260430T065740Z").length).toBeGreaterThan(0);
    });

    await waitFor(() => {
      expect(window.localStorage.getItem("ultrerp_legacy_refresh_active_job")).toBeNull();
    });

    expect(screen.queryByText("legacy-shadow-20260429T041104Z")).toBeNull();
    expect(screen.queryByText("canonical-import: connection has been released back to the pool")).toBeNull();
    expect(
      (screen.getByRole("button", { name: /quickActions\.incremental|Run Incremental Refresh/i }) as HTMLButtonElement)
        .disabled,
    ).toBe(false);
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

    fireEvent.change(document.getElementById("lsm-tenant-id") as HTMLInputElement, {
      target: { value: "tenant-1" },
    });

    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: /salesMonthly\.actions\.backfill|Backfill Range/i }),
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
      name: /salesMonthly\.actions\.repairMissing|Repair Missing/i,
    }) as HTMLButtonElement;
    expect(repairButton.disabled).toBe(true);

    fireEvent.change(document.getElementById("lsm-tenant-id") as HTMLInputElement, {
      target: { value: "tenant-1" },
    });

    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: /salesMonthly\.actions\.checkHealth|Check Health/i }),
      );
    });

    await waitFor(() => {
      expect(fetchSalesMonthlyHealthMock).toHaveBeenCalledWith(
        "tenant-1",
        expect.any(String),
        expect.any(String),
      );
    });

    expect(screen.getAllByText(/salesMonthly\.status\.healthy|Healthy/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/salesMonthly\.empty|No missing months|no gaps/i)).toBeTruthy();
    expect(repairButton.disabled).toBe(true);
  });
});