# Story 7.5: PostHog Integration — Visitor Tracking

Status: done

## Story

As a system,
I want to track website visitor sessions via PostHog,
So that we understand user behavior and can display traffic metrics on the dashboard.

## Acceptance Criteria

**AC1:** PostHog JS SDK initialized
**Given** the React app starts
**When** the app mounts
**Then** PostHog JS SDK is initialized with the project API key and host
**And** autocapture is enabled for clicks and interactions
**And** automatic page view capture is disabled (`capture_pageview: false`) — SPA hook handles page views
**And** session recording is disabled (privacy-first MVP)

**AC2:** Page views tracked
**Given** PostHog is initialized
**When** a user navigates between pages in the app
**Then** a `$pageview` event is sent to PostHog for each page view
**And** the event includes: URL, referrer, screen dimensions

**AC3:** Unique visitors identified
**Given** PostHog is tracking events
**When** events are sent
**Then** each visitor gets a distinct anonymous ID (PostHog default behavior)
**And** no personally identifiable information (PII) is sent to PostHog
**And** person profiles are set to `identified_only` (anonymous tracking base)

**AC4:** Configuration via environment
**Given** the app is deployed
**When** PostHog JS initializes
**Then** it reads the PostHog project API key from `VITE_POSTHOG_KEY` env variable
**And** it reads the PostHog host from `VITE_POSTHOG_HOST` env variable
**And** if neither is set, PostHog is NOT initialized (no errors)

**AC5:** PostHog disabled in development
**Given** the app is running in development mode
**When** PostHog config is not set
**Then** no PostHog requests are made
**And** no console errors appear
**And** the app functions normally without PostHog

**AC6:** Events flow to PostHog
**Given** PostHog JS is initialized in production
**When** visitors interact with the app
**Then** events appear in the PostHog dashboard within 10 minutes (NFR3)
**And** page views, sessions, and basic interactions are captured

## Tasks / Subtasks

- [ ] **Task 1: Install PostHog JS SDK** (AC1)
  - [ ] Add dependency: `pnpm add posthog-js`
  - [ ] Verify version compatibility with React 18+

- [ ] **Task 2: PostHog Provider Setup** (AC1, AC3, AC4, AC5)
  - [ ] Create `src/lib/posthog.ts`:
    ```typescript
    import posthog from 'posthog-js';

    const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY;
    const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST;

    export function initPostHog(): void {
      if (!POSTHOG_KEY || !POSTHOG_HOST) {
        console.info('[PostHog] Not configured — skipping initialization');
        return;
      }

      posthog.init(POSTHOG_KEY, {
        api_host: POSTHOG_HOST,
        person_profiles: 'identified_only',
        capture_pageview: false, // IMPORTANT: false — SPA pageviews handled by usePostHogPageView hook
        capture_pageleave: true,
        autocapture: true,
        disable_session_recording: true,
        persistence: 'localStorage+cookie',
        before_send: (event) => {
          // Strip PII from all events before they leave the browser
          const piiKeys = ['email', 'phone', 'name', 'address', 'contact_name',
                          'contact_phone', 'contact_email', 'billing_address'];
          if (event.properties) {
            for (const key of Object.keys(event.properties)) {
              if (piiKeys.some(pii => key.toLowerCase().includes(pii))) {
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
    ```

- [ ] **Task 3: Initialize in App Entry** (AC1)
  - [ ] Update `src/main.tsx`:
    ```typescript
    import { initPostHog } from './lib/posthog';
    initPostHog();
    // ... existing React render code
    ```
  - [ ] Ensure initialization happens before React render (top-level call)

- [ ] **Task 4: SPA Page View Tracking** (AC2)
  - [ ] Create `src/hooks/usePostHogPageView.ts`:
    ```typescript
    import { useEffect } from 'react';
    import { useLocation } from 'react-router-dom';
    import { posthog } from '../lib/posthog';

    export function usePostHogPageView(): void {
      const location = useLocation();
      useEffect(() => {
        if (posthog.__loaded) {
          posthog.capture('$pageview', {
            $current_url: window.location.href,
            $referrer: document.referrer || undefined,
            $screen_width: window.screen.width,
            $screen_height: window.screen.height,
          });
        }
      }, [location.pathname]);
    }
    ```
  - [ ] Call `usePostHogPageView()` in `App.tsx` (inside Router context)
  - [ ] NOTE: PostHog's autocapture handles initial page load. This hook handles SPA route changes.

- [ ] **Task 5: Environment Configuration** (AC4, AC5)
  - [ ] Add to `.env.example`:
    ```
    # PostHog Analytics (optional — leave empty to disable)
    VITE_POSTHOG_KEY=
    VITE_POSTHOG_HOST=
    ```
  - [ ] Add to `.env` (gitignored):
    ```
    VITE_POSTHOG_KEY=phc_your_project_key
    VITE_POSTHOG_HOST=https://us.posthog.com
    ```
  - [ ] Document in README that PostHog is optional and disabled by default

- [ ] **Task 6: Vite TypeScript Types** (AC4)
  - [ ] Add PostHog env vars to `src/vite-env.d.ts`:
    ```typescript
    interface ImportMetaEnv {
      readonly VITE_POSTHOG_KEY?: string;
      readonly VITE_POSTHOG_HOST?: string;
    }
    ```

- [ ] **Task 7: Frontend Tests** (AC1, AC4, AC5)
  - [ ] Create `src/tests/posthog/posthog-init.test.ts`:
    - Test: does not initialize when env vars missing
    - Test: initializes with correct config when env vars set
    - Mock `posthog.init` and verify call arguments
  - [ ] Create `src/tests/posthog/usePostHogPageView.test.tsx`:
    - Test: captures pageview on location change
    - Test: does not throw when PostHog not loaded

## Dev Notes

### Architecture Compliance

- **No backend changes:** This story is frontend-only. PostHog JS SDK runs client-side.
- **PostHog project API key vs Personal API key:** The frontend uses the **project API key** (`phc_...`) which is public and safe to expose in client-side code. The **Personal API key** (`phx_...`) is server-side only — used in Story 7.4's backend proxy. These are different keys.
- **New directories:**
  - `src/lib/posthog.ts` — PostHog initialization module
  - `src/hooks/usePostHogPageView.ts` — SPA page view tracking hook
  - `src/tests/posthog/` — PostHog test directory

### PostHog JS SDK Configuration

- **`person_profiles: 'identified_only'`** — Only creates person profiles when explicitly identified. Anonymous users get a distinct_id but no person profile. This is the privacy-respecting default.
- **`capture_pageview: false`** — MUST be false for SPA apps. If set to `true`, PostHog fires a pageview on initial load, then the `usePostHogPageView` hook (Task 4) also fires on initial mount — causing a **double pageview on every page load**. Set to `false` and let the hook handle ALL pageview tracking.
- **`autocapture: true`** — Captures clicks, form submissions, and other interactions automatically.
- **`disable_session_recording: true`** — Session replays disabled for MVP. Can be enabled later with explicit user consent.
- **`persistence: 'localStorage+cookie'`** — Persists distinct_id across sessions. Uses localStorage primarily, cookie as fallback.

### Critical Warnings

- **PostHog project API key is PUBLIC.** Unlike the Personal API key, the project key (`phc_...`) is designed to be exposed in client-side code. It can only ingest events, not read data. Do NOT confuse with the Personal API key.
- **Do NOT install `posthog-node`** — that's for Node.js backends. Use `posthog-js` for the React frontend.
- **SPA navigation:** PostHog's `capture_pageview: true` only fires on initial page load, and it WILL conflict with the React Router hook causing double events. For React Router SPA navigation, set `capture_pageview: false` and manually capture `$pageview` on ALL route changes (Task 4). This applies to all SPA frameworks.
- **CSP (Content Security Policy):** If the app has CSP headers, ensure PostHog's domain is allowed in `connect-src` and `script-src` directives. Currently no CSP is configured in the project; when one is added, include the PostHog host (e.g., `https://us.posthog.com`) in both directives.
- **Development mode:** PostHog will send events even in development if configured. Consider adding a `DEV` check to skip initialization entirely in development (not just debug mode). The current implementation only skips if env vars are empty.
- **Dependency on Story 7.1:** This story requires the App.tsx/Router structure from the dashboard page scaffold.
- **Independent of Story 7.4:** This story sets up tracking on the client side. Story 7.4 reads data from PostHog via the backend API. They can be developed in parallel.

### Previous Story Intelligence

- **Vite env vars:** Must be prefixed with `VITE_` to be exposed to the client bundle. Server-side env vars (like `POSTHOG_API_KEY` in Story 7.4) do NOT have this prefix.
- **React Router:** The project uses `react-router-dom` for routing. Verify by checking `package.json` dependencies.
- **TypeScript declarations:** Vite env vars should be typed in `src/vite-env.d.ts` for proper IntelliSense.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7, Story 7.5] AC definitions: track visitor sessions
- [Source: _bmad-output/planning-artifacts/epics.md#FR37] PostHog tracks website visitor sessions
- [Source: _bmad-output/planning-artifacts/epics.md#NFR3] PostHog events visible in dashboard: ≤ 10 minutes
- [Source: _bmad-output/planning-artifacts/epics.md#NFR24] PostHog: visitor tracking, goal conversion, dashboard integration
- [Source: posthog-js GitHub] PostHog JS SDK — init options, autocapture, SPA tracking
- [Source: https://posthog.com/docs/api/queries] PostHog uses HogQLQuery for data retrieval

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (via GitHub Copilot)

### Completion Notes List

- Story created after Context7 research on posthog-js SDK initialization and configuration
- SPA page view tracking pattern documented — PostHog autocapture only handles initial load
- Session recording explicitly disabled for privacy-first MVP approach
- Clarified the difference between project API key (public) and personal API key (secret)
- Development mode behavior documented — PostHog skipped when env vars empty
