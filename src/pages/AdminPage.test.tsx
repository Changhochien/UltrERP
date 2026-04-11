import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.resetModules();
});

describe("AdminPage", () => {
  it("creates a user from the admin dialog and refreshes the list", async () => {
    const refreshedUsers = [
      {
        id: "user-1",
        email: "owner@example.com",
        display_name: "Owner User",
        role: "owner",
        status: "active",
        created_at: "2025-01-01T00:00:00Z",
      },
      {
        id: "user-2",
        email: "new@example.com",
        display_name: "New User",
        role: "sales",
        status: "active",
        created_at: "2025-01-02T00:00:00Z",
      },
    ];
    const fetchUsersMock = vi
      .fn()
      .mockResolvedValue(refreshedUsers)
      .mockResolvedValueOnce([
        {
          id: "user-1",
          email: "owner@example.com",
          display_name: "Owner User",
          role: "owner",
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
        },
      ]);
    const fetchAuditLogsMock = vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });
    const createUserMock = vi.fn().mockResolvedValue({
      id: "user-2",
      email: "new@example.com",
      display_name: "New User",
      role: "sales",
      status: "active",
      created_at: "2025-01-02T00:00:00Z",
    });
    const updateUserMock = vi.fn();

    vi.doMock("../lib/api/admin", () => ({
      ADMIN_USER_ROLES: ["owner", "finance", "warehouse", "sales"],
      ADMIN_USER_STATUSES: ["active", "disabled"],
      fetchUsers: fetchUsersMock,
      fetchAuditLogs: fetchAuditLogsMock,
      createUser: createUserMock,
      updateUser: updateUserMock,
    }));

    const { AdminPage } = await import("./AdminPage");
    render(<MemoryRouter><AdminPage /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByText("owner@example.com")).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: "adminPage.users.addUser" }));
    fireEvent.change(screen.getByLabelText("adminPage.users.fields.email"), {
      target: { value: "new@example.com" },
    });
    fireEvent.change(screen.getByLabelText("adminPage.users.fields.displayName"), {
      target: { value: "New User" },
    });
    fireEvent.change(screen.getByLabelText("adminPage.users.fields.password"), {
      target: { value: "strongpass99" },
    });
    fireEvent.click(screen.getByRole("button", { name: "adminPage.users.dialog.createAction" }));

    await waitFor(() => {
      expect(createUserMock).toHaveBeenCalledWith({
        email: "new@example.com",
        display_name: "New User",
        role: "sales",
        password: "strongpass99",
      });
    });

    await waitFor(() => {
      expect(screen.getByText("new@example.com")).toBeTruthy();
    });
  });

  it("updates a user from the admin dialog", async () => {
    const updatedUsers = [
      {
        id: "user-1",
        email: "sales@example.com",
        display_name: "Sales Lead",
        role: "sales",
        status: "disabled",
        created_at: "2025-01-01T00:00:00Z",
      },
    ];
    const fetchUsersMock = vi
      .fn()
      .mockResolvedValue(updatedUsers)
      .mockResolvedValueOnce([
        {
          id: "user-1",
          email: "sales@example.com",
          display_name: "Sales User",
          role: "sales",
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
        },
      ]);
    const fetchAuditLogsMock = vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });
    const createUserMock = vi.fn();
    const updateUserMock = vi.fn().mockResolvedValue({
      id: "user-1",
      email: "sales@example.com",
      display_name: "Sales Lead",
      role: "sales",
      status: "disabled",
      created_at: "2025-01-01T00:00:00Z",
    });

    vi.doMock("../lib/api/admin", () => ({
      ADMIN_USER_ROLES: ["owner", "finance", "warehouse", "sales"],
      ADMIN_USER_STATUSES: ["active", "disabled"],
      fetchUsers: fetchUsersMock,
      fetchAuditLogs: fetchAuditLogsMock,
      createUser: createUserMock,
      updateUser: updateUserMock,
    }));

    const { AdminPage } = await import("./AdminPage");
    render(<MemoryRouter><AdminPage /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByText("sales@example.com")).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: "adminPage.users.editUser" }));
    fireEvent.change(screen.getByLabelText("adminPage.users.fields.displayName"), {
      target: { value: "Sales Lead" },
    });
    fireEvent.change(screen.getByLabelText("adminPage.users.fields.status"), {
      target: { value: "disabled" },
    });
    fireEvent.click(screen.getByRole("button", { name: "adminPage.users.dialog.save" }));

    await waitFor(() => {
      expect(updateUserMock).toHaveBeenCalledWith("user-1", {
        display_name: "Sales Lead",
        role: "sales",
        status: "disabled",
      });
    });

    await waitFor(() => {
      expect(screen.getByText("Sales Lead")).toBeTruthy();
    });
  });

  it("filters users by search text and status", async () => {
    const fetchUsersMock = vi.fn().mockResolvedValue([
      {
        id: "user-1",
        email: "owner@example.com",
        display_name: "Owner User",
        role: "owner",
        status: "active",
        created_at: "2025-01-01T00:00:00Z",
      },
      {
        id: "user-2",
        email: "disabled@example.com",
        display_name: "Disabled User",
        role: "sales",
        status: "disabled",
        created_at: "2025-01-02T00:00:00Z",
      },
    ]);
    const fetchAuditLogsMock = vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    vi.doMock("../lib/api/admin", () => ({
      ADMIN_USER_ROLES: ["owner", "finance", "warehouse", "sales"],
      ADMIN_USER_STATUSES: ["active", "disabled"],
      fetchUsers: fetchUsersMock,
      fetchAuditLogs: fetchAuditLogsMock,
      createUser: vi.fn(),
      updateUser: vi.fn(),
    }));

    const { AdminPage } = await import("./AdminPage");
    render(<MemoryRouter><AdminPage /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByText("owner@example.com")).toBeTruthy();
      expect(screen.getByText("disabled@example.com")).toBeTruthy();
    });

    expect(screen.getByRole("link", { name: "adminPage.settingsHub.openSettings" })).toBeTruthy();
    expect(screen.getByText("adminPage.permissions.title")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("adminPage.users.filters.search"), {
      target: { value: "disabled" },
    });

    await waitFor(() => {
      expect(screen.queryByText("owner@example.com")).toBeNull();
      expect(screen.getByText("disabled@example.com")).toBeTruthy();
    });

    fireEvent.change(screen.getByLabelText("adminPage.users.filters.search"), {
      target: { value: "" },
    });
    fireEvent.change(screen.getByLabelText("adminPage.users.filters.status"), {
      target: { value: "active" },
    });

    await waitFor(() => {
      expect(screen.getByText("owner@example.com")).toBeTruthy();
      expect(screen.queryByText("disabled@example.com")).toBeNull();
    });
  });

  it("passes audit explorer filters and presets into the audit API client", async () => {
    const formatDateInput = (date: Date) => {
      const year = date.getUTCFullYear();
      const month = String(date.getUTCMonth() + 1).padStart(2, "0");
      const day = String(date.getUTCDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    };
    const shiftUtcDays = (date: Date, days: number) => {
      const next = new Date(date);
      next.setUTCDate(next.getUTCDate() + days);
      return next;
    };
    const today = new Date();
    const todayValue = formatDateInput(today);
    const expectedCreatedAfter = `${formatDateInput(shiftUtcDays(today, -6))}T00:00:00`;
    const expectedCreatedBefore = `${todayValue}T23:59:59.999999`;

    const fetchUsersMock = vi.fn().mockResolvedValue([]);
    const fetchAuditLogsMock = vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    vi.doMock("../lib/api/admin", () => ({
      ADMIN_USER_ROLES: ["owner", "finance", "warehouse", "sales"],
      ADMIN_USER_STATUSES: ["active", "disabled"],
      fetchUsers: fetchUsersMock,
      fetchAuditLogs: fetchAuditLogsMock,
      createUser: vi.fn(),
      updateUser: vi.fn(),
    }));

    const { AdminPage } = await import("./AdminPage");
    render(<MemoryRouter><AdminPage /></MemoryRouter>);

    await waitFor(() => {
      expect(fetchAuditLogsMock).toHaveBeenCalledWith({
        page: 1,
        page_size: 20,
        action: undefined,
        actor_id: undefined,
        actor_type: undefined,
        entity_type: undefined,
        entity_id: undefined,
        created_after: undefined,
        created_before: undefined,
        sort_by: "created_at",
        sort_direction: "desc",
      });
    });

    fireEvent.change(screen.getByLabelText("adminPage.auditLog.filters.action"), {
      target: { value: "user.update" },
    });
    fireEvent.change(screen.getByLabelText("adminPage.auditLog.filters.actorType"), {
      target: { value: "user" },
    });
    fireEvent.click(screen.getByRole("button", { name: "adminPage.auditLog.presets.last7Days" }));

    await waitFor(() => {
      expect(fetchAuditLogsMock).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 20,
        action: "user.update",
        actor_id: undefined,
        actor_type: "user",
        entity_type: undefined,
        entity_id: undefined,
        created_after: expectedCreatedAfter,
        created_before: expectedCreatedBefore,
        sort_by: "created_at",
        sort_direction: "desc",
      });
    });
  });

  it("keeps audit log action options available after a selection", async () => {
    const fetchUsersMock = vi.fn().mockResolvedValue([]);
    const fetchAuditLogsMock = vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    vi.doMock("../lib/api/admin", () => ({
      ADMIN_USER_ROLES: ["owner", "finance", "warehouse", "sales"],
      ADMIN_USER_STATUSES: ["active", "disabled"],
      fetchUsers: fetchUsersMock,
      fetchAuditLogs: fetchAuditLogsMock,
      createUser: vi.fn(),
      updateUser: vi.fn(),
    }));

    const { AdminPage } = await import("./AdminPage");
    render(<MemoryRouter><AdminPage /></MemoryRouter>);

    const actionFilter = await screen.findByRole("combobox", {
      name: "adminPage.auditLog.filters.action",
    });

    expect(within(actionFilter).getByRole("option", { name: "user.update" })).toBeTruthy();
    expect(within(actionFilter).getByRole("option", { name: "approval.approve" })).toBeTruthy();

    fireEvent.change(actionFilter, {
      target: { value: "user.update" },
    });
    fireEvent.change(actionFilter, {
      target: { value: "approval.approve" },
    });

    await waitFor(() => {
      expect(fetchAuditLogsMock).toHaveBeenLastCalledWith(expect.objectContaining({
        action: "approval.approve",
      }));
    });
  });

  it("opens an audit detail sheet with state changes", async () => {
    const fetchUsersMock = vi.fn().mockResolvedValue([]);
    const fetchAuditLogsMock = vi.fn().mockResolvedValue({
      items: [
        {
          id: "audit-1",
          tenant_id: "tenant-1",
          actor_id: "owner@example.com",
          actor_type: "user",
          action: "user.update",
          entity_type: "user",
          entity_id: "user-1",
          before_state: { role: "sales" },
          after_state: { role: "owner" },
          correlation_id: "corr-1",
          notes: "Promoted during admin review",
          created_at: "2025-01-31T08:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    });

    vi.doMock("../lib/api/admin", () => ({
      ADMIN_USER_ROLES: ["owner", "finance", "warehouse", "sales"],
      ADMIN_USER_STATUSES: ["active", "disabled"],
      fetchUsers: fetchUsersMock,
      fetchAuditLogs: fetchAuditLogsMock,
      createUser: vi.fn(),
      updateUser: vi.fn(),
    }));

    const { AdminPage } = await import("./AdminPage");
    render(<MemoryRouter><AdminPage /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "adminPage.auditLog.actions.view" })).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: "adminPage.auditLog.actions.view" }));

    await waitFor(() => {
      expect(screen.getByText("adminPage.auditLog.detailSheet.title")).toBeTruthy();
      expect(screen.getByText("Promoted during admin review")).toBeTruthy();
      expect(screen.getByText(/"role": "sales"/)).toBeTruthy();
      expect(screen.getByText(/"role": "owner"/)).toBeTruthy();
    });
  });

  it("saves and reapplies an audit preset", async () => {
    const fetchUsersMock = vi.fn().mockResolvedValue([]);
    const fetchAuditLogsMock = vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    vi.doMock("../lib/api/admin", () => ({
      ADMIN_USER_ROLES: ["owner", "finance", "warehouse", "sales"],
      ADMIN_USER_STATUSES: ["active", "disabled"],
      fetchUsers: fetchUsersMock,
      fetchAuditLogs: fetchAuditLogsMock,
      createUser: vi.fn(),
      updateUser: vi.fn(),
    }));

    const { AdminPage } = await import("./AdminPage");
    render(<MemoryRouter><AdminPage /></MemoryRouter>);

    await waitFor(() => {
      expect(fetchAuditLogsMock).toHaveBeenCalled();
    });

    fireEvent.change(screen.getByLabelText("adminPage.auditLog.filters.actor"), {
      target: { value: "owner-1" },
    });
    fireEvent.change(screen.getByLabelText("adminPage.auditLog.filters.action"), {
      target: { value: "user.update" },
    });
    fireEvent.change(screen.getByLabelText("adminPage.auditLog.savedPresets.name"), {
      target: { value: "Month End" },
    });
    fireEvent.click(screen.getByRole("button", { name: "adminPage.auditLog.savedPresets.save" }));

    expect(localStorage.getItem("ultrerp_admin_audit_presets")).toContain("Month End");

    fireEvent.change(screen.getByLabelText("adminPage.auditLog.filters.actor"), {
      target: { value: "" },
    });
    fireEvent.change(screen.getByLabelText("adminPage.auditLog.filters.action"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Month End" }));

    await waitFor(() => {
      expect(fetchAuditLogsMock).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 20,
        action: "user.update",
        actor_id: "owner-1",
        actor_type: undefined,
        entity_type: undefined,
        entity_id: undefined,
        created_after: undefined,
        created_before: undefined,
        sort_by: "created_at",
        sort_direction: "desc",
      });
    });
  });

  it("pushes audit sort changes into the API query", async () => {
    const fetchUsersMock = vi.fn().mockResolvedValue([]);
    const fetchAuditLogsMock = vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    vi.doMock("../lib/api/admin", () => ({
      ADMIN_USER_ROLES: ["owner", "finance", "warehouse", "sales"],
      ADMIN_USER_STATUSES: ["active", "disabled"],
      fetchUsers: fetchUsersMock,
      fetchAuditLogs: fetchAuditLogsMock,
      createUser: vi.fn(),
      updateUser: vi.fn(),
    }));

    const { AdminPage } = await import("./AdminPage");
    render(<MemoryRouter><AdminPage /></MemoryRouter>);

    await waitFor(() => {
      expect(fetchAuditLogsMock).toHaveBeenCalledWith(expect.objectContaining({
        sort_by: "created_at",
        sort_direction: "desc",
      }));
    });

    fireEvent.click(screen.getByRole("button", { name: "adminPage.auditLog.columns.action" }));

    await waitFor(() => {
      expect(fetchAuditLogsMock).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 20,
        action: undefined,
        actor_id: undefined,
        actor_type: undefined,
        entity_type: undefined,
        entity_id: undefined,
        created_after: undefined,
        created_before: undefined,
        sort_by: "action",
        sort_direction: "asc",
      });
    });
  });

  it("exports the current audit page as JSON", async () => {
    const fetchUsersMock = vi.fn().mockResolvedValue([]);
    const fetchAuditLogsMock = vi.fn().mockResolvedValue({
      items: [
        {
          id: "audit-2",
          tenant_id: "tenant-1",
          actor_id: "owner@example.com",
          actor_type: "user",
          action: "user.update",
          entity_type: "user",
          entity_id: "user-2",
          before_state: null,
          after_state: { role: "finance" },
          correlation_id: "corr-2",
          notes: "Updated access",
          created_at: "2025-02-01T08:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    });
    let exportedBlob: Blob | null = null;
    const originalCreateElement = document.createElement.bind(document);
    const mockAnchor = originalCreateElement("a");
    mockAnchor.click = vi.fn();

    vi.doMock("../lib/api/admin", () => ({
      ADMIN_USER_ROLES: ["owner", "finance", "warehouse", "sales"],
      ADMIN_USER_STATUSES: ["active", "disabled"],
      fetchUsers: fetchUsersMock,
      fetchAuditLogs: fetchAuditLogsMock,
      createUser: vi.fn(),
      updateUser: vi.fn(),
    }));
    vi.spyOn(document, "createElement").mockImplementation(((tagName: string) => {
      if (tagName === "a") {
        return mockAnchor;
      }
      return originalCreateElement(tagName);
    }) as typeof document.createElement);
    globalThis.URL.createObjectURL = vi.fn((blob: Blob) => {
      exportedBlob = blob;
      return "blob:test";
    });
    globalThis.URL.revokeObjectURL = vi.fn();

    const { AdminPage } = await import("./AdminPage");
    render(<MemoryRouter><AdminPage /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "adminPage.auditLog.export.json" })).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: "adminPage.auditLog.export.json" }));

    expect(mockAnchor.click).toHaveBeenCalled();
    expect(exportedBlob).toBeTruthy();
    expect(exportedBlob!.type).toBe("application/json;charset=utf-8;");
    expect(mockAnchor.download).toMatch(/^audit-log-\d{4}-\d{2}-\d{2}\.json$/);
  });
});