# Story 7.6: PostHog Integration — Goal Conversions

Status: done

## Story

As a system,
I want to track goal conversions (visitor → inquiry) via PostHog,
So that we measure marketing effectiveness and display conversion trends on the dashboard.

## Acceptance Criteria

**AC1:** Inquiry event tracked
**Given** PostHog JS is initialized (Story 7.5)
**When** a visitor completes an inquiry action (e.g., submits a contact form, requests a quote)
**Then** a custom event `inquiry_submitted` is captured in PostHog
**And** the event includes properties: `inquiry_type`, `source_page`

**AC2:** Conversion event definition
**Given** PostHog receives events
**When** a visitor who had `$pageview` events also has an `inquiry_submitted` event in the same session
**Then** this constitutes a conversion (visitor → inquiry)
**And** PostHog's built-in funnel/conversion features can compute this

**AC3:** Conversion rate on dashboard
**Given** Story 7.4 already displays conversion rate from the PostHog API
**When** inquiry events are tracked (this story)
**Then** the conversion rate in Story 7.4's widget becomes meaningful (non-zero)
**And** the conversion rate = `(unique inquiry submitters / unique visitors) * 100`

**AC4:** Trend data available
**Given** goal conversions are tracked over time
**When** an owner wants to compare conversion trends
**Then** PostHog's built-in Trends feature shows conversion rates over time
**And** the ERP dashboard can extend in a future story to show trend charts

**AC5:** Custom event helper
**Given** a developer needs to track a custom PostHog event
**When** they use the tracking utility
**Then** a reusable helper function is available: `trackEvent(eventName, properties)`
**And** the helper gracefully handles PostHog not being initialized

**AC6:** No PII in events
**Given** custom events are captured
**When** the event payload is constructed
**Then** no personally identifiable information is included
**And** no customer names, emails, or phone numbers are sent to PostHog

## Tasks / Subtasks

- [ ] **Task 1: Event Tracking Utility** (AC1, AC5, AC6)
  - [ ] Create `src/lib/analytics.ts`:
    ```typescript
    import { posthog } from './posthog';

    /**
     * Track a custom analytics event via PostHog.
     * No-ops gracefully if PostHog is not initialized.
     */
    export function trackEvent(
      eventName: string,
      properties?: Record<string, string | number | boolean>,
    ): void {
      if (posthog?.__loaded) {
        const safeProps = properties ? sanitizeProperties(properties) : undefined;
        posthog.capture(eventName, safeProps);
      }
    }

    // Pre-defined event names for type safety
    export const AnalyticsEvents = {
      INQUIRY_SUBMITTED: 'inquiry_submitted',
      QUOTE_REQUESTED: 'quote_requested',
      CONTACT_FORM_SUBMITTED: 'contact_form_submitted',
    } as const;
    ```

- [ ] **Task 2: Integrate Inquiry Tracking** (AC1, AC2)
  - [ ] Identify the inquiry/contact form component(s) in the app
    - NOTE: If no inquiry form exists yet (this is an internal ERP, not a customer-facing website), create a placeholder integration point:
      - Add `trackEvent(AnalyticsEvents.INQUIRY_SUBMITTED, { inquiry_type: 'general', source_page: location.pathname })` as a reusable call
      - Document that this event should be fired from the customer-facing website's contact form when it is built
  - [ ] For the ERP itself, track key business actions as proxy conversions:
    - Order creation → `trackEvent('order_created', { source_page: '/orders' })`
    - Customer creation → `trackEvent('customer_created', { source_page: '/customers' })`
    - These serve as internal KPIs until a customer-facing website exists

- [ ] **Task 3: PostHog Dashboard Configuration** (AC2, AC4)
  - [ ] Document how to create a PostHog Insight for conversion tracking:
    - Create a Funnel insight: Step 1 = `$pageview`, Step 2 = `inquiry_submitted`
    - Create a Trends insight: `inquiry_submitted` events over time
    - Save these as reusable insights in the PostHog dashboard
  - [ ] This is a **manual configuration step**, not code — document in README or ops docs

- [ ] **Task 4: No-PII Enforcement** (AC6)
  - [ ] Add a `sanitizeProperties` function to `src/lib/analytics.ts`:
    ```typescript
    const PII_KEYS = [
      'email', 'phone', 'name', 'address', 'ssn',
      'contact_name', 'contact_phone', 'contact_email',
      'billing_address', 'business_number',
    ];

    export function sanitizeProperties(
      props: Record<string, unknown>,
    ): Record<string, string | number | boolean> {
      const sanitized: Record<string, string | number | boolean> = {};
      for (const [key, value] of Object.entries(props)) {
        if (PII_KEYS.some(pii => key.toLowerCase().includes(pii))) {
          continue; // Strip PII fields
        }
        if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
          sanitized[key] = value;
        }
      }
      return sanitized;
    }
    ```
  - [ ] Use `sanitizeProperties` in `trackEvent` before calling `posthog.capture`

- [ ] **Task 5: Frontend Tests** (AC1, AC5, AC6)
  - [ ] Create `src/tests/posthog/analytics.test.ts`:
    - Test: `trackEvent` calls `posthog.capture` when loaded
    - Test: `trackEvent` no-ops when PostHog not loaded
    - Test: `sanitizeProperties` strips email, phone, name fields
    - Test: `sanitizeProperties` passes through safe properties
    - Test: `AnalyticsEvents` constants match expected event names

- [ ] **Task 6: Integrate into Dashboard Page** (AC3)
  - [ ] Verify Story 7.4's `VisitorStatsCard` already displays conversion rate
  - [ ] No additional dashboard widget needed — conversion rate is already shown in Story 7.4
  - [ ] Add documentation note: conversion rate will be 0 until `inquiry_submitted` events are tracked

## Dev Notes

### Architecture Compliance

- **Frontend-only story:** No backend changes. Custom events are captured by PostHog JS and sent directly to PostHog's ingestion endpoint.
- **New files:**
  - `src/lib/analytics.ts` — event tracking utility and PII sanitizer
- **No new components:** Conversion data is already displayed by Story 7.4's `VisitorStatsCard`

### PostHog Custom Events

- **Event naming:** Use `snake_case` for PostHog event names (PostHog convention). Prefix with domain if needed (e.g., `erp_order_created`).
- **Properties:** Keep properties flat (no nested objects). Use primitive types only: string, number, boolean.
- **Event → Insight mapping:**
  - `inquiry_submitted` → Conversion funnel (visitor → inquiry)
  - `$pageview` → Unique visitors count
  - Both are queried by Story 7.4's backend proxy via HogQLQuery

### Critical Warnings

- **This is an internal ERP, not a customer-facing website.** The original PRD mentions "website visitors" which implies a separate customer-facing website. For the ERP admin panel, tracking internal user actions (order creation, customer creation) as proxy KPIs is appropriate. When a customer-facing website is built, the same PostHog project can track actual visitor → inquiry conversions.
- **PostHog JS `capture()` is fire-and-forget.** It queues events locally and sends them in batches. No need for error handling on individual captures.
- **Do NOT track sensitive business data.** Do not send amounts, customer IDs, or order details to PostHog. Track only action types and source pages for aggregate metrics.
- **Dependency on Story 7.5:** PostHog JS must be initialized (Story 7.5) before any custom events can be captured.
- **Dependency on Story 7.4:** The conversion rate display is handled by Story 7.4's dashboard widget. This story provides the event data that makes that display meaningful.

### PII Protection Strategy

- **Blocklist approach:** `sanitizeProperties` strips any property whose key contains PII-related terms (email, phone, name, address, ssn, contact_name, contact_phone, contact_email, billing_address, business_number)
- **Defense in depth:** Even if a developer accidentally passes PII, the sanitizer catches it before it reaches PostHog. The `before_send` hook in Story 7.5 provides a second layer, and `sanitizeProperties` in `trackEvent` (this story) provides a first layer.
- **`tax_id` removed from blocklist:** The codebase uses `business_number` (Taiwan 統一編號), not `tax_id`. `business_number` is a public business registration number, but included in blocklist as a precaution.

### Previous Story Intelligence

- **PostHog initialization:** Story 7.5 creates `src/lib/posthog.ts` and initializes PostHog globally. This story's `analytics.ts` imports from that module.
- **No existing analytics:** The project has no prior analytics tracking. This is the first analytics integration.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7, Story 7.6] AC definitions: goal conversions
- [Source: _bmad-output/planning-artifacts/epics.md#FR38] PostHog tracks goal conversions (visitor → inquiry)
- [Source: _bmad-output/planning-artifacts/epics.md#FR39] PostHog data visible in dashboard within 10 minutes
- [Source: _bmad-output/planning-artifacts/prd.md#Success Metrics] Website → leads: visitor-to-inquiry conversion rate improving by ≥20%
- [Source: posthog-js GitHub] PostHog JS SDK — capture() method, custom events
- [Source: https://posthog.com/docs/api/queries] HogQLQuery for querying inquiry_submitted events (used by Story 7.4)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (via GitHub Copilot)

### Completion Notes List

- Story created after analyzing the distinction between internal ERP tracking and customer-facing website tracking
- PII sanitization utility designed as defense-in-depth for PostHog event properties
- Custom event names follow PostHog snake_case convention
- Documented that this is an internal ERP — true visitor→inquiry conversion requires a customer-facing website
- Proxy KPIs defined: order_created and customer_created as internal metrics until external website exists
