import { afterEach, describe, expect, it, vi } from "vitest";

const {
  isPermissionGrantedMock,
  isTauriMock,
  requestPermissionMock,
  sendNotificationMock,
} = vi.hoisted(() => ({
  isPermissionGrantedMock: vi.fn(async () => false),
  isTauriMock: vi.fn(() => false),
  requestPermissionMock: vi.fn<() => Promise<NotificationPermission>>(async () => "denied"),
  sendNotificationMock: vi.fn(() => undefined),
}));

vi.mock("@tauri-apps/api/core", () => ({
  isTauri: isTauriMock,
}));

vi.mock("@tauri-apps/plugin-notification", () => ({
  isPermissionGranted: isPermissionGrantedMock,
  requestPermission: requestPermissionMock,
  sendNotification: sendNotificationMock,
}));

import { notifyDesktop } from "../notifications";

afterEach(() => {
  isPermissionGrantedMock.mockClear();
  isPermissionGrantedMock.mockResolvedValue(false);
  isTauriMock.mockClear();
  isTauriMock.mockReturnValue(false);
  requestPermissionMock.mockClear();
  requestPermissionMock.mockResolvedValue("denied");
  sendNotificationMock.mockClear();
  vi.restoreAllMocks();
});

describe("desktop notifications", () => {
  it("no-ops outside the desktop shell", async () => {
    await expect(
      notifyDesktop({ title: "Invoice", body: "Updated" }),
    ).resolves.toEqual({ delivered: false });

    expect(isPermissionGrantedMock).not.toHaveBeenCalled();
    expect(sendNotificationMock).not.toHaveBeenCalled();
  });

  it("requests permission and sends the notification when granted", async () => {
    isTauriMock.mockReturnValue(true);
    requestPermissionMock.mockResolvedValue("granted");

    await expect(
      notifyDesktop({ title: "Invoice", body: "Updated" }),
    ).resolves.toEqual({ delivered: true });

    expect(isPermissionGrantedMock).toHaveBeenCalledTimes(1);
    expect(requestPermissionMock).toHaveBeenCalledTimes(1);
    expect(sendNotificationMock).toHaveBeenCalledWith({
      title: "Invoice",
      body: "Updated",
    });
  });

  it("returns a graceful non-delivery result when permission is denied", async () => {
    isTauriMock.mockReturnValue(true);

    await expect(
      notifyDesktop({ title: "Invoice", body: "Updated" }),
    ).resolves.toEqual({ delivered: false });

    expect(sendNotificationMock).not.toHaveBeenCalled();
  });
});