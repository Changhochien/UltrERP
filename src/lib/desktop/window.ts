import { isTauri } from "@tauri-apps/api/core";

export function isDesktopShell(): boolean {
  return isTauri();
}

async function getCurrentDesktopWindow() {
  const { getCurrentWindow } = await import("@tauri-apps/api/window");
  return getCurrentWindow();
}

export async function showWindow(): Promise<void> {
  if (!isDesktopShell()) {
    return;
  }

  try {
    const window = await getCurrentDesktopWindow();
    if (await window.isMinimized()) {
      await window.unminimize();
    }
    await window.show();
    await window.setFocus();
  } catch (error) {
    console.warn("Failed to restore the desktop window.", error);
  }
}

export async function hideWindowToTray(): Promise<void> {
  if (!isDesktopShell()) {
    return;
  }

  try {
    const window = await getCurrentDesktopWindow();
    await window.hide();
  } catch (error) {
    console.warn("Failed to hide the desktop window to tray.", error);
  }
}

export async function isDesktopWindowVisible(): Promise<boolean> {
  if (!isDesktopShell()) {
    return true;
  }

  try {
    const window = await getCurrentDesktopWindow();
    return await window.isVisible();
  } catch (error) {
    console.warn("Failed to read desktop window visibility.", error);
    return true;
  }
}