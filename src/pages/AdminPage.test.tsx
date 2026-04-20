import { act, cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

const dataTableMock = vi.hoisted(() => ({
  auditSortChange: undefined as ((next: { columnId: string; direction: "asc" | "desc" } | null) => void) | undefined,
}));

const fetchUsersMock = vi.hoisted(() => vi.fn());
const fetchAuditLogsMock = vi.hoisted(() => vi.fn());
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
});