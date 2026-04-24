import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

const dataTableMock = vi.hoisted(() => ({
  auditSortChange: undefined as ((next: { columnId: string; direction: "asc" | "desc" } | null) => void) | undefined,
}));

const fetchUsersMock = vi.hoisted(() => vi.fn());
const fetchAuditLogsMock = vi.hoisted(() => vi.fn());
const fetchLegacyRefreshLanesMock = vi.hoisted(() => vi.fn());
const fetchLegacyRefreshRecentRunsMock = vi.hoisted(() => vi.fn());
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
  });
});