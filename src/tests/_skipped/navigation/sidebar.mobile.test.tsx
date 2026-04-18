import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { AppNavigation } from "../../components/AppNavigation";
import { ThemeProvider } from "../../components/theme/ThemeProvider";
import { SidebarProvider, SidebarTrigger } from "../../components/ui/sidebar";
import { AuthProvider } from "../../hooks/useAuth";
import { clearTestToken, setTestToken } from "../helpers/auth";

vi.mock("../../hooks/useIsMobile", () => ({
  useIsMobile: () => true,
}));

function renderMobileNavigation() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <ThemeProvider>
        <AuthProvider>
          <SidebarProvider>
            <SidebarTrigger />
            <AppNavigation />
          </SidebarProvider>
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

describe("mobile sidebar", () => {
  it("closes the navigation drawer after a route selection", async () => {
    setTestToken("admin");
    renderMobileNavigation();
    const customersLinkName = /Customers|客戶/;

    const trigger = screen.getByRole("button", { name: "Toggle navigation" });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(trigger);
    expect(trigger.getAttribute("aria-expanded")).toBe("true");

    fireEvent.click(await screen.findByRole("link", { name: customersLinkName }));

    await waitFor(() => {
      expect(trigger.getAttribute("aria-expanded")).toBe("false");
    });
    expect(screen.queryByRole("link", { name: customersLinkName })).toBeNull();
  });
});