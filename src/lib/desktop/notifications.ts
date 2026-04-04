import { isTauri } from "@tauri-apps/api/core";

export interface DesktopNotificationRequest {
  title: string;
  body: string;
}

export interface DesktopNotificationResult {
  delivered: boolean;
}

export async function notifyDesktop(
  notification: DesktopNotificationRequest,
): Promise<DesktopNotificationResult> {
  if (!isTauri()) {
    return { delivered: false };
  }

  try {
    const plugin = await import("@tauri-apps/plugin-notification");
    let permissionGranted = await plugin.isPermissionGranted();
    if (!permissionGranted) {
      permissionGranted = (await plugin.requestPermission()) === "granted";
    }

    if (!permissionGranted) {
      return { delivered: false };
    }

    await Promise.resolve(plugin.sendNotification(notification));
    return { delivered: true };
  } catch (error) {
    console.warn("Failed to send a desktop notification.", error);
    return { delivered: false };
  }
}