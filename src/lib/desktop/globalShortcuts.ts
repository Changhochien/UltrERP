import { isTauri } from "@tauri-apps/api/core";

import { toTauriShortcut, type PreparedShortcutBinding } from "../shortcuts";

export interface DesktopShortcutRegistration {
  id: string;
  binding: PreparedShortcutBinding;
}

export function isDesktopShell(): boolean {
  return isTauri();
}

export async function registerDesktopShortcuts(
  shortcuts: readonly DesktopShortcutRegistration[],
  onTrigger: (shortcutId: string) => void,
  shouldContinue: () => boolean = () => true,
): Promise<() => Promise<void>> {
  if (!isDesktopShell() || shortcuts.length === 0 || !shouldContinue()) {
    return async () => undefined;
  }

  const plugin = await import("@tauri-apps/plugin-global-shortcut");
  if (!shouldContinue()) {
    return async () => undefined;
  }

  const registeredShortcuts: string[] = [];

  for (const shortcut of shortcuts) {
    if (!shouldContinue()) {
      break;
    }

    const tauriShortcut = toTauriShortcut(shortcut.binding);

    try {
      if (await plugin.isRegistered(tauriShortcut)) {
        registeredShortcuts.push(tauriShortcut);
        continue;
      }

      await plugin.register(tauriShortcut, (event) => {
        if (event.state !== "Released") {
          return;
        }
        onTrigger(shortcut.id);
      });

      registeredShortcuts.push(tauriShortcut);
    } catch (error) {
      console.warn(`Failed to register desktop shortcut ${tauriShortcut}.`, error);
    }
  }

  const cleanup = async () => {
    if (registeredShortcuts.length === 0) {
      return;
    }

    try {
      await plugin.unregister(registeredShortcuts);
    } catch (error) {
      console.warn("Failed to unregister desktop shortcuts during cleanup.", error);
    }
  };

  const handleBeforeUnload = () => {
    void cleanup();
  };

  window.addEventListener("beforeunload", handleBeforeUnload, { once: true });

  return async () => {
    window.removeEventListener("beforeunload", handleBeforeUnload);
    await cleanup();
  };
}