import { useEffect } from "react";

import { refreshInvoiceEguiStatus } from "../../lib/api/invoices";
import {
  DESKTOP_EGUI_POLL_INTERVAL_MS,
  runDesktopEguiNotificationCycle,
} from "../../lib/desktop/eguiMonitor";
import { notifyDesktop } from "../../lib/desktop/notifications";
import { isDesktopShell, isDesktopWindowVisible } from "../../lib/desktop/window";

export function DesktopTrayController() {
  useEffect(() => {
    if (!isDesktopShell()) {
      return undefined;
    }

    let cancelled = false;
    let inFlight = false;

    const runCycle = async () => {
      if (cancelled || inFlight) {
        return;
      }

      inFlight = true;
      try {
        await runDesktopEguiNotificationCycle({
          isWindowVisible: isDesktopWindowVisible,
          refreshInvoiceStatus: refreshInvoiceEguiStatus,
          notify: notifyDesktop,
          onError: (message, error) => {
            console.warn(message, error);
          },
        });
      } finally {
        inFlight = false;
      }
    };

    void runCycle();
    const intervalId = window.setInterval(() => {
      void runCycle();
    }, DESKTOP_EGUI_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  return null;
}