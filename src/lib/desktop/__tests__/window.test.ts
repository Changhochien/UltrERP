import { afterEach, describe, expect, it, vi } from "vitest";

const {
  desktopWindow,
  getCurrentWindowMock,
  isTauriMock,
} = vi.hoisted(() => {
  const windowApi = {
    hide: vi.fn(async () => undefined),
    isMinimized: vi.fn(async () => false),
    isVisible: vi.fn(async () => true),
    setFocus: vi.fn(async () => undefined),
    show: vi.fn(async () => undefined),
    unminimize: vi.fn(async () => undefined),
  };

  return {
    desktopWindow: windowApi,
    getCurrentWindowMock: vi.fn(() => windowApi),
    isTauriMock: vi.fn(() => false),
  };
});

vi.mock("@tauri-apps/api/core", () => ({
  isTauri: isTauriMock,
}));

vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: getCurrentWindowMock,
}));

import {
  hideWindowToTray,
  isDesktopShell,
  isDesktopWindowVisible,
  showWindow,
} from "../window";

afterEach(() => {
  getCurrentWindowMock.mockClear();
  isTauriMock.mockReturnValue(false);
  desktopWindow.hide.mockClear();
  desktopWindow.isMinimized.mockClear();
  desktopWindow.isMinimized.mockResolvedValue(false);
  desktopWindow.isVisible.mockClear();
  desktopWindow.isVisible.mockResolvedValue(true);
  desktopWindow.setFocus.mockClear();
  desktopWindow.show.mockClear();
  desktopWindow.unminimize.mockClear();
  vi.restoreAllMocks();
});

describe("desktop window bridge", () => {
  it("reports web mode when Tauri is unavailable", () => {
    expect(isDesktopShell()).toBe(false);
  });

  it("restores the desktop window when running inside Tauri", async () => {
    isTauriMock.mockReturnValue(true);
    desktopWindow.isMinimized.mockResolvedValue(true);

    await showWindow();

    expect(getCurrentWindowMock).toHaveBeenCalledTimes(1);
    expect(desktopWindow.unminimize).toHaveBeenCalledTimes(1);
    expect(desktopWindow.show).toHaveBeenCalledTimes(1);
    expect(desktopWindow.setFocus).toHaveBeenCalledTimes(1);
  });

  it("hides the desktop window to tray when running inside Tauri", async () => {
    isTauriMock.mockReturnValue(true);

    await hideWindowToTray();

    expect(desktopWindow.hide).toHaveBeenCalledTimes(1);
  });

  it("reads the current desktop visibility when running inside Tauri", async () => {
    isTauriMock.mockReturnValue(true);
    desktopWindow.isVisible.mockResolvedValue(false);

    await expect(isDesktopWindowVisible()).resolves.toBe(false);
  });
});