/** PostHog analytics initialization. */

import posthog from "posthog-js";

const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY;
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST;

export const PII_KEYS = [
  "email",
  "phone",
  "name",
  "address",
  "ssn",
  "contact_name",
  "contact_phone",
  "contact_email",
  "billing_address",
  "business_number",
];

export function initPostHog(): void {
  if (!POSTHOG_KEY || !POSTHOG_HOST) {
    return;
  }

  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    person_profiles: "identified_only",
    capture_pageview: false,
    capture_pageleave: true,
    autocapture: true,
    disable_session_recording: true,
    persistence: "localStorage+cookie",
    before_send: (event) => {
      if (event?.properties) {
        for (const key of Object.keys(event.properties)) {
          if (PII_KEYS.some((pii) => key.toLowerCase().includes(pii))) {
            delete event.properties[key];
          }
        }
      }
      return event;
    },
    loaded: (ph) => {
      if (import.meta.env.DEV) {
        ph.debug();
      }
    },
  });
}

export { posthog };
