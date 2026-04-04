/** Tests for auth context, ProtectedRoute, permissions, and LoginPage. */

import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppNavigation } from "../../components/AppNavigation";
import { AuthProvider, useAuth } from "../../hooks/useAuth";
import { type AppFeature, usePermissions } from "../../hooks/usePermissions";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { apiFetch } from "../../lib/apiFetch";
import LoginPage from "../../pages/LoginPage";
import { setTestToken, clearTestToken } from "../helpers/auth";

afterEach(() => {
  window.location.hash = "";
  clearTestToken();
  cleanup();
  vi.restoreAllMocks();
});

/* ─── helpers ─── */

function PermissionsDisplay() {
  const { canAccess, canWrite } = usePermissions();
  const features: AppFeature[] = ["dashboard", "inventory", "customers", "invoices", "orders", "payments", "admin"];
  return (
    <ul>
      {features.map((f) => (
        <li key={f}>
          <span data-testid={`${f}-access`}>{f}: {canAccess(f) ? "yes" : "no"}</span>
          <span data-testid={`${f}-write`}>{f}: {canWrite(f) ? "yes" : "no"}</span>
        </li>
      ))}
    </ul>
  );
}

function AuthDisplay() {
  const { user, isAuthenticated, logout } = useAuth();
  return (
    <div>
      <span data-testid="authed">{isAuthenticated ? "yes" : "no"}</span>
      <span data-testid="role">{user?.role ?? "none"}</span>
      <button type="button" onClick={logout}>Logout</button>
    </div>
  );
}

function renderWithAuth(ui: React.ReactElement, { route = "/" } = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AuthProvider>{ui}</AuthProvider>
    </MemoryRouter>,
  );
}

/* ─── useAuth ─── */

describe("useAuth", () => {
  it("returns unauthenticated when no token", () => {
    renderWithAuth(<AuthDisplay />);
    expect(screen.getByTestId("authed").textContent).toBe("no");
    expect(screen.getByTestId("role").textContent).toBe("none");
  });

  it("reads valid token from localStorage", () => {
    setTestToken("finance");
    renderWithAuth(<AuthDisplay />);
    expect(screen.getByTestId("authed").textContent).toBe("yes");
    expect(screen.getByTestId("role").textContent).toBe("finance");
  });

  it("clears token on logout", () => {
    setTestToken("owner");
    renderWithAuth(<AuthDisplay />);
    expect(screen.getByTestId("authed").textContent).toBe("yes");
    fireEvent.click(screen.getByText("Logout"));
    expect(screen.getByTestId("authed").textContent).toBe("no");
    expect(localStorage.getItem("ultrerp_token")).toBeNull();
  });
});

/* ─── usePermissions ─── */

describe("usePermissions", () => {
  it("owner can access everything", () => {
    setTestToken("owner");
    renderWithAuth(<PermissionsDisplay />);
    expect(screen.getByTestId("dashboard-access").textContent).toContain("yes");
    expect(screen.getByTestId("admin-access").textContent).toContain("yes");
    expect(screen.getByTestId("payments-access").textContent).toContain("yes");
    expect(screen.getByTestId("inventory-access").textContent).toContain("yes");
    expect(screen.getByTestId("inventory-write").textContent).toContain("yes");
  });

  it("finance cannot access inventory, orders, admin", () => {
    setTestToken("finance");
    renderWithAuth(<PermissionsDisplay />);
    expect(screen.getByTestId("dashboard-access").textContent).toContain("yes");
    expect(screen.getByTestId("customers-access").textContent).toContain("yes");
    expect(screen.getByTestId("invoices-access").textContent).toContain("yes");
    expect(screen.getByTestId("payments-access").textContent).toContain("yes");
    expect(screen.getByTestId("inventory-access").textContent).toContain("no");
    expect(screen.getByTestId("orders-access").textContent).toContain("no");
    expect(screen.getByTestId("admin-access").textContent).toContain("no");
    expect(screen.getByTestId("customers-write").textContent).toContain("no");
    expect(screen.getByTestId("invoices-write").textContent).toContain("yes");
  });

  it("warehouse sees dashboard, inventory, orders only", () => {
    setTestToken("warehouse");
    renderWithAuth(<PermissionsDisplay />);
    expect(screen.getByTestId("dashboard-access").textContent).toContain("yes");
    expect(screen.getByTestId("inventory-access").textContent).toContain("yes");
    expect(screen.getByTestId("orders-access").textContent).toContain("yes");
    expect(screen.getByTestId("customers-access").textContent).toContain("no");
    expect(screen.getByTestId("invoices-access").textContent).toContain("no");
    expect(screen.getByTestId("payments-access").textContent).toContain("no");
    expect(screen.getByTestId("inventory-write").textContent).toContain("yes");
    expect(screen.getByTestId("orders-write").textContent).toContain("no");
  });

  it("sales sees dashboard, inventory, customers, invoices, orders", () => {
    setTestToken("sales");
    renderWithAuth(<PermissionsDisplay />);
    expect(screen.getByTestId("dashboard-access").textContent).toContain("yes");
    expect(screen.getByTestId("inventory-access").textContent).toContain("yes");
    expect(screen.getByTestId("customers-access").textContent).toContain("yes");
    expect(screen.getByTestId("invoices-access").textContent).toContain("yes");
    expect(screen.getByTestId("orders-access").textContent).toContain("yes");
    expect(screen.getByTestId("payments-access").textContent).toContain("no");
    expect(screen.getByTestId("admin-access").textContent).toContain("no");
    expect(screen.getByTestId("inventory-write").textContent).toContain("no");
    expect(screen.getByTestId("customers-write").textContent).toContain("yes");
    expect(screen.getByTestId("invoices-write").textContent).toContain("no");
  });
});

describe("AppNavigation", () => {
  it("filters menu items by role", () => {
    setTestToken("finance");
    renderWithAuth(<AppNavigation />);

    expect(screen.getByRole("link", { name: "Dashboard" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Customers" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Invoices" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Payments" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Inventory" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Orders" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Admin" })).toBeNull();
  });
});

/* ─── ProtectedRoute ─── */

describe("ProtectedRoute", () => {
  it("redirects to /login when not authenticated", () => {
    render(
      <MemoryRouter initialEntries={["/secret"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div>Login Page</div>} />
            <Route
              path="/secret"
              element={
                <ProtectedRoute>
                  <div>Secret Content</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByText("Login Page")).toBeTruthy();
    expect(screen.queryByText("Secret Content")).toBeNull();
  });

  it("renders children when authenticated", () => {
    setTestToken("owner");
    render(
      <MemoryRouter initialEntries={["/secret"]}>
        <AuthProvider>
          <Routes>
            <Route
              path="/secret"
              element={
                <ProtectedRoute>
                  <div>Secret Content</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByText("Secret Content")).toBeTruthy();
  });

  it("redirects to dashboard when missing required feature", () => {
    setTestToken("warehouse"); // no customers access
    render(
      <MemoryRouter initialEntries={["/customers"]}>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<div>Dashboard</div>} />
            <Route
              path="/customers"
              element={
                <ProtectedRoute requiredFeature="customers">
                  <div>Customers</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByText("Dashboard")).toBeTruthy();
    expect(screen.queryByText("Customers")).toBeNull();
  });
});

/* ─── LoginPage ─── */

describe("LoginPage", () => {
  it("redirects authenticated users back to the dashboard", () => {
    setTestToken("owner");
    renderWithAuth(
      <Routes>
        <Route path="/" element={<div>Dashboard</div>} />
        <Route path="/login" element={<LoginPage />} />
      </Routes>,
      { route: "/login" },
    );
    expect(screen.getByText("Dashboard")).toBeTruthy();
    expect(screen.queryByLabelText("Email")).toBeNull();
  });

  it("renders email and password fields", () => {
    renderWithAuth(
      <Routes>
        <Route path="*" element={<LoginPage />} />
      </Routes>,
    );
    expect(screen.getByLabelText("Email")).toBeTruthy();
    expect(screen.getByLabelText("Password")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Log in" })).toBeTruthy();
  });

  it("shows error on failed login", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Invalid credentials" }), { status: 401 }),
    );

    renderWithAuth(
      <Routes>
        <Route path="*" element={<LoginPage />} />
      </Routes>,
    );

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "bad@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Log in" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeTruthy();
    });
  });

  it("clears auth state and redirects to login on 401 responses", async () => {
    setTestToken("owner");
    window.location.hash = "#/invoices";
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(null, { status: 401 }));

    renderWithAuth(<AuthDisplay />);
    expect(screen.getByTestId("authed").textContent).toBe("yes");

    await apiFetch("/api/v1/invoices");

    await waitFor(() => {
      expect(screen.getByTestId("authed").textContent).toBe("no");
    });
    expect(window.location.hash).toBe("#/login");
  });
});
