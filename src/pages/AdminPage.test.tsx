import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.resetModules();
});

describe("AdminPage", () => {
  it("creates a user from the admin dialog and refreshes the list", async () => {
    const fetchUsersMock = vi
      .fn()
      .mockResolvedValueOnce([
        {
          id: "user-1",
          email: "owner@example.com",
          display_name: "Owner User",
          role: "owner",
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
        },
      ])
      .mockResolvedValueOnce([
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
      ]);
    const fetchAuditLogsMock = vi.fn().mockResolvedValue([]);
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
    const fetchUsersMock = vi
      .fn()
      .mockResolvedValueOnce([
        {
          id: "user-1",
          email: "sales@example.com",
          display_name: "Sales User",
          role: "sales",
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
        },
      ])
      .mockResolvedValueOnce([
        {
          id: "user-1",
          email: "sales@example.com",
          display_name: "Sales Lead",
          role: "sales",
          status: "disabled",
          created_at: "2025-01-01T00:00:00Z",
        },
      ]);
    const fetchAuditLogsMock = vi.fn().mockResolvedValue([]);
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
    const fetchAuditLogsMock = vi.fn().mockResolvedValue([]);

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

  it("passes audit explorer filters into the audit API client", async () => {
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
        entity_type: undefined,
        entity_id: undefined,
      });
    });

    fireEvent.change(screen.getByLabelText("adminPage.auditLog.filters.action"), {
      target: { value: "user.update" },
    });

    await waitFor(() => {
      expect(fetchAuditLogsMock).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 20,
        action: "user.update",
        actor_id: undefined,
        entity_type: undefined,
        entity_id: undefined,
      });
    });
  });
});