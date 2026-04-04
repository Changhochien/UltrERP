import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("../../lib/posthog", () => {
  const posthog = {
    __loaded: true,
    capture: vi.fn(),
  };
  const PII_KEYS = [
    "email", "phone", "name", "address", "ssn",
    "contact_name", "contact_phone", "contact_email",
    "billing_address", "business_number",
  ];
  return { posthog, PII_KEYS };
});

import { trackEvent, sanitizeProperties, AnalyticsEvents } from "../../lib/analytics";
import { posthog } from "../../lib/posthog";

describe("analytics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetModules();
  });

  describe("trackEvent", () => {
    it("calls posthog.capture when loaded", () => {
      trackEvent("test_event", { page: "/home" });
      expect(posthog.capture).toHaveBeenCalledWith("test_event", {
        page: "/home",
      });
    });

    it("no-ops when PostHog not loaded", () => {
      const ph = posthog as unknown as Record<string, unknown>;
      const original = ph.__loaded;
      ph.__loaded = false;
      trackEvent("test_event", { page: "/x" });
      expect(posthog.capture).not.toHaveBeenCalled();
      ph.__loaded = original;
    });

    it("calls capture without properties when none given", () => {
      trackEvent("bare_event");
      expect(posthog.capture).toHaveBeenCalledWith("bare_event", undefined);
    });
  });

  describe("sanitizeProperties", () => {
    it("strips PII fields (email, phone, name, address)", () => {
      const result = sanitizeProperties({
        email: "test@example.com",
        phone: "0912345678",
        contact_name: "Alice",
        billing_address: "123 Street",
        safe_field: "ok",
      });
      expect(result).toEqual({ safe_field: "ok" });
    });

    it("strips business_number", () => {
      const result = sanitizeProperties({
        business_number: "12345678",
        source_page: "/orders",
      });
      expect(result).toEqual({ source_page: "/orders" });
    });

    it("passes through safe string, number, boolean properties", () => {
      const result = sanitizeProperties({
        page: "/home",
        count: 5,
        active: true,
      });
      expect(result).toEqual({ page: "/home", count: 5, active: true });
    });

    it("drops non-primitive values (objects, arrays, null, undefined)", () => {
      const result = sanitizeProperties({
        nested: { a: 1 },
        list: [1, 2],
        empty: null,
        missing: undefined,
        ok: "yes",
      });
      expect(result).toEqual({ ok: "yes" });
    });

    it("is case-insensitive for PII matching", () => {
      const result = sanitizeProperties({
        Email: "x@y.com",
        USER_PHONE: "123",
        safe: "yes",
      });
      expect(result).toEqual({ safe: "yes" });
    });
  });

  describe("AnalyticsEvents", () => {
    it("has expected event names", () => {
      expect(AnalyticsEvents.INQUIRY_SUBMITTED).toBe("inquiry_submitted");
      expect(AnalyticsEvents.QUOTE_REQUESTED).toBe("quote_requested");
      expect(AnalyticsEvents.CONTACT_FORM_SUBMITTED).toBe("contact_form_submitted");
      expect(AnalyticsEvents.ORDER_CREATED).toBe("order_created");
      expect(AnalyticsEvents.CUSTOMER_CREATED).toBe("customer_created");
    });
  });
});
