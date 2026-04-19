import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const {
  desktopShortcutState,
  isDesktopShellMock,
  registerDesktopShortcutsMock,
} = vi.hoisted(() => {
  const state = {
    trigger: null as ((shortcutId: string) => void) | null,
  };

  return {
    desktopShortcutState: state,
    isDesktopShellMock: vi.fn(() => false),
    registerDesktopShortcutsMock: vi.fn(async (_shortcuts, onTrigger: (shortcutId: string) => void) => {
      state.trigger = onTrigger;
      return async () => {
        state.trigger = null;
      };
    }),
  };
});

vi.mock("../../lib/desktop/globalShortcuts", () => ({
  isDesktopShell: isDesktopShellMock,
  registerDesktopShortcuts: registerDesktopShortcutsMock,
}));

import { ShortcutLayer } from "../../components/shortcuts/ShortcutLayer";
import { AuthProvider } from "../../hooks/useAuth";
import {
  CUSTOMER_CREATE_ROUTE,
  CUSTOMERS_ROUTE,
  HOME_ROUTE,
  INVENTORY_ROUTE,
  INVOICES_ROUTE,
  ORDER_CREATE_ROUTE,
  ORDERS_ROUTE,
  PAYMENTS_ROUTE,
} from "../../lib/routes";
import { clearTestToken, setTestToken } from "../helpers/auth";

afterEach(() => {
  window.location.hash = "";
  clearTestToken();
  desktopShortcutState.trigger = null;
  isDesktopShellMock.mockReturnValue(false);
  registerDesktopShortcutsMock.mockClear();
  cleanup();
  vi.restoreAllMocks();
});

function ShortcutHarness() {
  return (
    <>
      <ShortcutLayer />
      <label>
        Editor input
        <input aria-label="Editor input" />
      </label>
      <div aria-label="Rich editor" contentEditable role="textbox" tabIndex={0} />
      <Routes>
        <Route path={HOME_ROUTE} element={<div>Dashboard Screen</div>} />
        <Route path={INVENTORY_ROUTE} element={<div>Inventory Screen</div>} />
        <Route path={CUSTOMERS_ROUTE} element={<div>Customers Screen</div>} />
        <Route path={CUSTOMER_CREATE_ROUTE} element={<div>Create Customer Screen</div>} />
        <Route path={INVOICES_ROUTE} element={<div>Invoices Screen</div>} />
        <Route path={ORDERS_ROUTE} element={<div>Orders Screen</div>} />
        <Route path={ORDER_CREATE_ROUTE} element={<div>Create Order Screen</div>} />
        <Route path={PAYMENTS_ROUTE} element={<div>Payments Screen</div>} />
      </Routes>
    </>
  );
}

function renderHarness(route = HOME_ROUTE) {
  setTestToken("owner");

  return render(
    <MemoryRouter initialEntries={[route]}>
      <AuthProvider>
        <ShortcutHarness />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("ShortcutLayer", () => {
  it("opens the overlay with question mark and closes it with Escape", () => {
    renderHarness();

    fireEvent.keyDown(window, { code: "Slash", key: "?", shiftKey: true });
    expect(screen.getByRole("dialog", { name: "Keyboard shortcuts" })).toBeTruthy();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Keyboard shortcuts" })).toBeNull();
  });

  it("opens the overlay with Mod+/", () => {
    renderHarness();

    fireEvent.keyDown(window, { code: "Slash", ctrlKey: true, key: "/" });

    expect(screen.getByRole("dialog", { name: "Keyboard shortcuts" })).toBeTruthy();
  });

  it("does not advertise desktop-only shortcuts in web mode", () => {
    renderHarness();

    fireEvent.keyDown(window, { code: "Slash", key: "?", shiftKey: true });

    expect(screen.queryByText(/Desktop /i)).toBeNull();
  });

  it("lists screen-local shortcuts from the shared registry", () => {
    renderHarness(CUSTOMERS_ROUTE);

    fireEvent.keyDown(window, { code: "Slash", key: "?", shiftKey: true });

    expect(screen.getByText("New customer")).toBeTruthy();
    expect(screen.getByText("Go to customers")).toBeTruthy();
  });

  it("dispatches global and screen-local shortcuts outside editable fields", () => {
    renderHarness();

    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "c" });
    expect(screen.getByText("Customers Screen")).toBeTruthy();

    fireEvent.keyDown(window, { key: "c" });
    fireEvent.keyDown(window, { key: "n" });
    expect(screen.getByText("Create Customer Screen")).toBeTruthy();
  });

  it("suppresses shortcuts while typing in native inputs and rich textboxes", () => {
    renderHarness(CUSTOMERS_ROUTE);

    const input = screen.getByLabelText("Editor input");
    input.focus();
    fireEvent.keyDown(input, { key: "c" });
    fireEvent.keyDown(input, { key: "n" });
    expect(screen.queryByText("Create Customer Screen")).toBeNull();

    const richTextbox = screen.getByRole("textbox", { name: "Rich editor" });
    richTextbox.focus();
    fireEvent.keyDown(richTextbox, { key: "g" });
    fireEvent.keyDown(richTextbox, { key: "o" });
    expect(screen.queryByText("Orders Screen")).toBeNull();
    expect(screen.getByText("Customers Screen")).toBeTruthy();
  });

  it("suppresses desktop shortcut callbacks while typing in editable fields", async () => {
    renderHarness();
    await waitFor(() => expect(desktopShortcutState.trigger).not.toBeNull());

    const input = screen.getByLabelText("Editor input");
    input.focus();
    desktopShortcutState.trigger?.("open-shortcuts");
    expect(screen.queryByRole("dialog", { name: "Keyboard shortcuts" })).toBeNull();
  });

  it("keeps focus inside the overlay while tabbing", () => {
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback: FrameRequestCallback) => {
      callback(0);
      return 1;
    });
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => undefined);

    renderHarness();
    fireEvent.keyDown(window, { code: "Slash", key: "?", shiftKey: true });

    const closeButton = screen.getByRole("button", { name: "Close" });
    expect(document.activeElement).toBe(closeButton);

    fireEvent.keyDown(window, { key: "Tab" });
    expect(document.activeElement).toBe(closeButton);
  });
});