import { useEffect, useLayoutEffect } from "react";

import { useAuth } from "../../hooks/useAuth";
import { refreshInvoiceEguiStatus } from "../../lib/api/invoices";
import {
  DESKTOP_EGUI_POLL_INTERVAL_MS,
  runDesktopEguiNotificationCycle,
  synchronizeTrackedEguiScope,
} from "../../lib/desktop/eguiMonitor";
import { notifyDesktop } from "../../lib/desktop/notifications";
import { isDesktopShell, isDesktopWindowVisible } from "../../lib/desktop/window";

export function DesktopTrayController() {
  const { user } = useAuth();

  useLayoutEffect(() => {
    if (!user) {
      return;
    }

    synchronizeTrackedEguiScope(`${user.tenant_id}:${user.sub}`);
  }, [user?.sub, user?.tenant_id]);

  useEffect(() => {
    if (!user || !isDesktopShell()) {
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
          shouldContinue: () => !cancelled,
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
  }, [user?.sub, user?.tenant_id]);

  return null;
}