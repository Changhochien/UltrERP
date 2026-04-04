import { afterEach, describe, expect, it, vi } from "vitest";

import {
  DESKTOP_EGUI_STORAGE_KEY,
  rememberTrackedEguiInvoice,
  runDesktopEguiNotificationCycle,
  shouldNotifyEguiTransition,
} from "../eguiMonitor";

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe("eguiMonitor", () => {
  it("tracks the latest viewed eGUI invoice state locally", () => {
    rememberTrackedEguiInvoice({
      id: "inv-1",
      invoice_number: "AA00000001",
      egui_submission: {
        status: "PENDING",
        mode: "mock",
        retry_count: 0,
        deadline_at: "2026-04-04T00:00:00Z",
        deadline_label: "48-hour submission window",
        is_overdue: false,
        updated_at: "2026-04-04T00:00:00Z",
      },
    });

    const persisted = JSON.parse(
      localStorage.getItem(DESKTOP_EGUI_STORAGE_KEY) ?? "{}",
    ) as Record<string, { lastSeenStatus: string; invoiceNumber: string }>;

    expect(persisted["inv-1"]?.lastSeenStatus).toBe("PENDING");
    expect(persisted["inv-1"]?.invoiceNumber).toBe("AA00000001");
  });

  it("notifies once for a meaningful hidden transition and persists the new state", async () => {
    rememberTrackedEguiInvoice({
      id: "inv-1",
      invoice_number: "AA00000001",
      egui_submission: {
        status: "QUEUED",
        mode: "mock",
        retry_count: 0,
        deadline_at: "2026-04-04T00:00:00Z",
        deadline_label: "48-hour submission window",
        is_overdue: false,
        updated_at: "2026-04-04T00:00:00Z",
      },
    });

    const notify = vi.fn(async () => ({ delivered: true }));

    await runDesktopEguiNotificationCycle({
      isWindowVisible: async () => false,
      refreshInvoiceStatus: async () => ({ status: "SENT" as const }),
      notify,
      now: () => "2026-04-04T12:00:00Z",
    });

    const persisted = JSON.parse(
      localStorage.getItem(DESKTOP_EGUI_STORAGE_KEY) ?? "{}",
    ) as Record<string, { lastSeenStatus: string; lastNotifiedStatus?: string }>;

    expect(notify).toHaveBeenCalledTimes(1);
    expect(persisted["inv-1"]?.lastSeenStatus).toBe("SENT");
    expect(persisted["inv-1"]?.lastNotifiedStatus).toBe("SENT");
  });

  it("does not refresh or notify while the window is visible", async () => {
    rememberTrackedEguiInvoice({
      id: "inv-1",
      invoice_number: "AA00000001",
      egui_submission: {
        status: "QUEUED",
        mode: "mock",
        retry_count: 0,
        deadline_at: "2026-04-04T00:00:00Z",
        deadline_label: "48-hour submission window",
        is_overdue: false,
        updated_at: "2026-04-04T00:00:00Z",
      },
    });

    const refreshInvoiceStatus = vi.fn(async () => ({ status: "SENT" as const }));
    const notify = vi.fn(async () => ({ delivered: true }));

    await runDesktopEguiNotificationCycle({
      isWindowVisible: async () => true,
      refreshInvoiceStatus,
      notify,
    });

    expect(refreshInvoiceStatus).not.toHaveBeenCalled();
    expect(notify).not.toHaveBeenCalled();
  });

  it("suppresses replay when the tracked status has already been notified", async () => {
    rememberTrackedEguiInvoice({
      id: "inv-1",
      invoice_number: "AA00000001",
      egui_submission: {
        status: "SENT",
        mode: "mock",
        retry_count: 0,
        deadline_at: "2026-04-04T00:00:00Z",
        deadline_label: "48-hour submission window",
        is_overdue: false,
        updated_at: "2026-04-04T00:00:00Z",
      },
    });
    localStorage.setItem(
      DESKTOP_EGUI_STORAGE_KEY,
      JSON.stringify({
        "inv-1": {
          invoiceId: "inv-1",
          invoiceNumber: "AA00000001",
          lastSeenStatus: "SENT",
          lastNotifiedStatus: "SENT",
          updatedAt: "2026-04-04T00:00:00Z",
        },
      }),
    );

    const notify = vi.fn(async () => ({ delivered: true }));

    await runDesktopEguiNotificationCycle({
      isWindowVisible: async () => false,
      refreshInvoiceStatus: async () => ({ status: "SENT" as const }),
      notify,
    });

    expect(notify).not.toHaveBeenCalled();
  });

  it("treats only meaningful eGUI transitions as notification-worthy", () => {
    expect(shouldNotifyEguiTransition("QUEUED", "SENT")).toBe(true);
    expect(shouldNotifyEguiTransition("SENT", "ACKED")).toBe(true);
    expect(shouldNotifyEguiTransition("PENDING", "QUEUED")).toBe(false);
    expect(shouldNotifyEguiTransition("ACKED", "ACKED")).toBe(false);
  });
});