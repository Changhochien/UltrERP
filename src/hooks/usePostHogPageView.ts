/** Track SPA page views via PostHog. */

import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import { posthog } from "../lib/posthog";

export function usePostHogPageView(): void {
  const location = useLocation();

  useEffect(() => {
    if (posthog.__loaded) {
      posthog.capture("$pageview", {
        $current_url: window.location.href,
        $referrer: document.referrer || undefined,
        $screen_width: window.screen.width,
        $screen_height: window.screen.height,
      });
    }
  }, [location.pathname]);
}
