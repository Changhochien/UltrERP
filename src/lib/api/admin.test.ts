import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.fn();

vi.mock("../apiFetch", () => ({
  apiFetch: (...args: Parameters<typeof apiFetchMock>) => apiFetchMock(...args),
}));

afterEach(() => {
  vi.clearAllMocks();
  vi.resetModules();
});

describe("admin api client", () => {
  it("posts create user payload to the admin users endpoint", async () => {
    apiFetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "user-1",
          email: "new@example.com",
          display_name: "New User",
          role: "sales",
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
        }),
        {
          status: 201,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    const { createUser } = await import("./admin");
    await createUser({
      email: "new@example.com",
      password: "strongpass99",
      display_name: "New User",
      role: "sales",
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/admin/users/",
      expect.objectContaining({ method: "POST" }),
    );
    expect(JSON.parse(apiFetchMock.mock.calls[0][1].body)).toEqual({
      email: "new@example.com",
      password: "strongpass99",
      display_name: "New User",
      role: "sales",
    });
  });

  it("patches update user payload to the user detail endpoint", async () => {
    apiFetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "user-1",
          email: "new@example.com",
          display_name: "Updated User",
          role: "finance",
          status: "disabled",
          created_at: "2025-01-01T00:00:00Z",
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    const { updateUser } = await import("./admin");
    await updateUser("user-1", {
      display_name: "Updated User",
      role: "finance",
      status: "disabled",
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/admin/users/user-1",
      expect.objectContaining({ method: "PATCH" }),
    );
    expect(JSON.parse(apiFetchMock.mock.calls[0][1].body)).toEqual({
      display_name: "Updated User",
      role: "finance",
      status: "disabled",
    });
  });

  it("builds audit log query params for the admin audit explorer", async () => {
    apiFetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], total: 0, page: 2, page_size: 20 }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    const { fetchAuditLogs } = await import("./admin");
    await fetchAuditLogs({
      page: 2,
      page_size: 20,
      actor_id: "owner-1",
      action: "user.update",
      entity_type: "user",
      entity_id: "abc123",
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/admin/audit-logs/?page=2&page_size=20&action=user.update&actor_id=owner-1&entity_type=user&entity_id=abc123",
    );
  });
});