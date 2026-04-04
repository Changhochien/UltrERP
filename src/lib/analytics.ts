/** Custom event tracking utility for PostHog analytics. */

import { posthog, PII_KEYS } from "./posthog";

/** Strip PII fields from event properties. */
export function sanitizeProperties(
  props: Record<string, unknown>,
): Record<string, string | number | boolean> {
  const sanitized: Record<string, string | number | boolean> = {};
  for (const [key, value] of Object.entries(props)) {
    if (PII_KEYS.some((pii) => key.toLowerCase().includes(pii))) {
      continue;
    }
    if (
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean"
    ) {
      sanitized[key] = value;
    }
  }
  return sanitized;
}

/**
 * Track a custom analytics event via PostHog.
 * No-ops gracefully if PostHog is not initialized.
 */
export function trackEvent(
  eventName: string,
  properties?: Record<string, string | number | boolean>,
): void {
  if (posthog?.__loaded) {
    const safeProps = properties
      ? sanitizeProperties(properties)
      : undefined;
    posthog.capture(eventName, safeProps);
  }
}

/** Pre-defined event names for type safety. */
export const AnalyticsEvents = {
  INQUIRY_SUBMITTED: "inquiry_submitted",
  QUOTE_REQUESTED: "quote_requested",
  CONTACT_FORM_SUBMITTED: "contact_form_submitted",
  ORDER_CREATED: "order_created",
  CUSTOMER_CREATED: "customer_created",
} as const;
