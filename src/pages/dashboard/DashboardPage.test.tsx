import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ThemeProvider } from "../../components/theme/ThemeProvider";
import { AuthProvider } from "../../hooks/useAuth";
import { clearTestToken, setTestToken } from "../../tests/helpers/auth";
import { DashboardPage } from "./DashboardPage";

vi.mock("../../domain/dashboard/hooks/useDashboard", () => ({
  useRevenueSummary: () => ({ data: null, isLoading: false, error: null }),
}));

vi.mock("../../domain/dashboard/components/RevenueCard", () => ({
  RevenueCard: () => <div>RevenueCard</div>,
}));

vi.mock("../../domain/dashboard/components/TopProductsCard", () => ({
  TopProductsCard: () => <div>TopProductsCard</div>,
}));

vi.mock("../../domain/dashboard/components/VisitorStatsCard", () => ({
  VisitorStatsCard: () => <div>VisitorStatsCard</div>,
}));

vi.mock("../../domain/dashboard/components/LowStockAlertsCard", () => ({
  LowStockAlertsCard: () => <div>LowStockAlertsCard</div>,
}));

function renderDashboard() {
  return render(
    <MemoryRouter>
      <ThemeProvider>
        <AuthProvider>
          <DashboardPage />
        </AuthProvider>
      </ThemeProvider>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  clearTestToken();
  vi.restoreAllMocks();
});

describe("DashboardPage", () => {
  it("hides low-stock alerts for roles without inventory access", () => {
    setTestToken("finance");
    renderDashboard();

    expect(screen.queryByText("LowStockAlertsCard")).toBeNull();
  });

  it("renders low-stock alerts for admin users", () => {
    setTestToken("admin");
    renderDashboard();

    expect(screen.getByText("LowStockAlertsCard")).toBeTruthy();
  });
});