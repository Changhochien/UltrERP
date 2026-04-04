# Story 7.4: PostHog Visitor Count on Dashboard

Status: done

## Story

As an owner,
I want to see PostHog visitor count from the previous day on the dashboard,
So that I can track website traffic alongside business metrics.

## Acceptance Criteria

**AC1:** Yesterday's visitor count displayed
**Given** PostHog is configured with a valid API key
**When** I view the dashboard
**Then** I see yesterday's unique visitor count
**And** the count is fetched from the PostHog Query API

**AC2:** Conversion rate displayed
**Given** PostHog tracks visitor sessions and inquiry events
**When** I view the dashboard
**Then** I see the conversion rate: `(unique inquiry submitters / unique visitors) * 100`
**And** the rate is displayed as a percentage with 1 decimal place
**And** "unique" means `COUNT(DISTINCT distinct_id)` — not total event count

**AC3:** Data freshness
**Given** PostHog events have a ≤ 10-minute ingestion delay (NFR3)
**When** the dashboard loads
**Then** the visitor count reflects data up to ~10 minutes ago
**And** the data label shows "Yesterday" with the actual date

**AC4:** PostHog API error handling
**Given** the PostHog API is unreachable or returns an error
**When** the dashboard loads
**Then** the visitor count widget shows a user-friendly error state: "Analytics unavailable"
**And** the error is logged server-side (not exposed to the user)
**And** other dashboard widgets continue to render normally

**AC5:** PostHog not configured
**Given** PostHog API key or project ID is not set in environment variables
**When** the dashboard loads
**Then** the visitor count widget shows: "Analytics not configured"
**And** no API call is attempted

**AC6:** Backend proxy endpoint
**Given** the backend is running with PostHog credentials
**When** I call `GET /api/v1/dashboard/visitor-stats`
**Then** the response includes: `visitor_count`, `inquiry_count`, `conversion_rate`, `date`
**And** the backend proxies the request to PostHog API (frontend never calls PostHog directly)
**And** PostHog Personal API key is stored server-side only

**AC7:** Auto-refresh
**Given** the dashboard is open
**When** 5 minutes have elapsed
**Then** the visitor stats auto-refresh without full page reload

## Tasks / Subtasks

- [ ] **Task 1: Backend Configuration** (AC5, AC6)
  - [ ] Add environment variables to `.env` and document in README:
    ```
    POSTHOG_API_KEY=phx_...        # Personal API key (server-side only)
    POSTHOG_PROJECT_ID=12345       # PostHog project ID
    POSTHOG_HOST=https://us.posthog.com  # or self-hosted instance
    ```
  - [ ] Add to existing `Settings` class in `backend/common/config.py`:
    ```python
    posthog_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("POSTHOG_API_KEY", "posthog_api_key"),
    )
    posthog_project_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("POSTHOG_PROJECT_ID", "posthog_project_id"),
    )
    posthog_host: str = Field(
        default="https://us.posthog.com",
        validation_alias=AliasChoices("POSTHOG_HOST", "posthog_host"),
    )
    ```
    NOTE: Config is `backend/common/config.py`, NOT `backend/app/config.py`. Uses `pydantic_settings.BaseSettings` with `AliasChoices` pattern.

- [ ] **Task 2: PostHog Client Service** (AC1, AC2, AC6)
  - [ ] Create `backend/domains/dashboard/posthog_client.py`:
    - Use `httpx.AsyncClient` for async HTTP calls to PostHog
    - Implement `get_visitor_stats(yesterday: date) -> VisitorStats`:
      - **IMPORTANT:** Compute yesterday as `datetime.now(UTC).date() - timedelta(days=1)`, NOT `date.today()`
      - POST to `{POSTHOG_HOST}/api/projects/{project_id}/query/`
      - Query: HogQLQuery getting unique visitor count for yesterday
        ```json
        {
          "query": {
            "kind": "HogQLQuery",
            "query": "SELECT count(DISTINCT distinct_id) FROM events WHERE event = '$pageview' AND timestamp >= toDate('YYYY-MM-DD') AND timestamp < toDate('YYYY-MM-DD') + INTERVAL 1 DAY"
          }
        }
        ```
      - Second query for inquiry count:
        ```json
        {
          "query": {
            "kind": "HogQLQuery",
            "query": "SELECT count(DISTINCT distinct_id) FROM events WHERE event = 'inquiry_submitted' AND timestamp >= toDate('YYYY-MM-DD') AND timestamp < toDate('YYYY-MM-DD') + INTERVAL 1 DAY"
          }
        }
        ```
    - Handle connection errors gracefully → return `None`
    - Implement connection timeout (10 seconds)

- [ ] **Task 3: Visitor Stats Schema** (AC6)
  - [ ] Add to `backend/domains/dashboard/schemas.py`:
    ```python
    class VisitorStatsResponse(BaseModel):
        visitor_count: int
        inquiry_count: int
        conversion_rate: Decimal | None  # None if visitor_count = 0
        date: date
        is_configured: bool  # False if PostHog keys not set
        error: str | None  # Error message if API call failed
    ```

- [ ] **Task 4: Visitor Stats Route** (AC4, AC5, AC6)
  - [ ] `GET /visitor-stats` → `get_visitor_stats_endpoint()`:
    - Check if PostHog is configured → return `is_configured=False` if not
    - Call PostHog client service
    - If error → return with `error` message, visitor_count=0
    - If success → compute conversion_rate and return
    - Add to existing dashboard router

- [ ] **Task 5: Frontend — Visitor Stats Card** (AC1, AC2, AC3, AC4, AC5, AC7)
  - [ ] Create `src/domain/dashboard/components/VisitorStatsCard.tsx`:
    - Display yesterday's visitor count with large number
    - Display conversion rate as percentage
    - Show date label: "Yesterday (YYYY-MM-DD)"
    - Error state: "Analytics unavailable"
    - Not-configured state: "Analytics not configured"
    - Loading skeleton state
  - [ ] Add to `src/lib/api/dashboard.ts`:
    - `fetchVisitorStats(): Promise<VisitorStatsResponse>`
  - [ ] Add types to `src/domain/dashboard/types.ts`:
    ```typescript
    export interface VisitorStatsResponse {
      visitor_count: number;
      inquiry_count: number;
      conversion_rate: string | null;
      date: string;
      is_configured: boolean;
      error: string | null;
    }
    ```
  - [ ] Add to `src/domain/dashboard/hooks/useDashboard.ts`:
    - `useVisitorStats()` — fetches on mount, auto-refreshes every 5 minutes

- [ ] **Task 6: Integrate into Dashboard Page** (AC1)
  - [ ] Add `VisitorStatsCard` to `DashboardPage.tsx` grid

- [ ] **Task 7: Backend Tests** (AC1, AC2, AC4, AC5)
  - [ ] Create `backend/tests/domains/dashboard/test_visitor_stats.py`
  - [ ] Test: PostHog not configured → returns is_configured=False
  - [ ] Test: PostHog API returns visitor data → correct response
  - [ ] Test: PostHog API error → returns error message, visitor_count=0
  - [ ] Test: conversion rate calculation (visitors=100, inquiries=5 → 5.0%)
  - [ ] Test: zero visitors → conversion_rate=None
  - [ ] Mock `httpx.AsyncClient` for all PostHog API calls

- [ ] **Task 8: Frontend Tests** (AC1, AC4, AC5, AC7)
  - [ ] Create `src/domain/dashboard/__tests__/VisitorStatsCard.test.tsx`
  - [ ] Test: renders visitor count and conversion rate
  - [ ] Test: error state renders "Analytics unavailable"
  - [ ] Test: not-configured state renders message
  - [ ] Test: auto-refresh calls fetch after interval

## Dev Notes

### Architecture Compliance

- **Backend proxy pattern:** The frontend never calls PostHog directly. All PostHog API calls go through the backend proxy endpoint. This keeps the PostHog Personal API key server-side only (security requirement).
- **HTTP client:** Uses `httpx.AsyncClient` — already a project dependency (`httpx>=0.28.1` in pyproject.toml). Do NOT add `requests` (blocking).
- **No database interaction:** This endpoint does not touch the local database. No `set_tenant` needed. No SQLAlchemy session needed.

### PostHog API Integration

- **API endpoint:** `POST {host}/api/projects/{project_id}/query/`
- **Auth:** Bearer token with Personal API key: `Authorization: Bearer phx_...`
- **Query language:** HogQLQuery — PostHog's SQL dialect
- **Visitor count query:**
  ```sql
  SELECT count(DISTINCT distinct_id)
  FROM events
  WHERE event = '$pageview'
    AND timestamp >= toDate('2026-04-01')
    AND timestamp < toDate('2026-04-01') + INTERVAL 1 DAY
  ```
- **Inquiry count query:**
  ```sql
  SELECT count(DISTINCT distinct_id)
  FROM events
  WHERE event = 'inquiry_submitted'
    AND timestamp >= toDate('2026-04-01')
    AND timestamp < toDate('2026-04-01') + INTERVAL 1 DAY
  ```
- **Rate limits:** PostHog API: 2400 req/hr, 240 req/min, 3 concurrent. Dashboard refreshes every 5 min = ~288 req/day per user. Well within limits.

### Critical Warnings

- **PostHog API key is a SECRET.** It must NEVER be exposed to the frontend or committed to version control. Store in `.env` and load via environment variables. Add `POSTHOG_API_KEY` to `.env.example` with a placeholder value.
- **httpx dependency:** Already in `pyproject.toml` as `httpx>=0.28.1`. No need to add it. Do NOT use `requests` (blocking).
- **PostHog query response format:** The `results` field from HogQLQuery is a 2D array: `[[count_value]]`. Parse carefully: `response["results"][0][0]`.
- **Timezone awareness (CRITICAL):** PostHog timestamps are UTC. When computing "yesterday", you **MUST** use `datetime.now(UTC).date() - timedelta(days=1)`, **NOT** `date.today()`. Using `date.today()` gives the *local* date which will produce wrong results in non-UTC timezones (e.g., Taiwan is UTC+8, so `date.today()` at 2am local is still "yesterday" in UTC). The HogQL `toDate()` function also operates in UTC.
- **Auto-refresh:** Use `setInterval` in the React hook with cleanup on unmount. Be mindful of memory leaks.
- **Dependency on Story 7.1:** This story extends the dashboard page and domain.
- **Dependency on Story 7.5/7.6:** The visitor and inquiry data only exists in PostHog if tracking is set up (Stories 7.5, 7.6). If tracking isn't configured yet, this widget will show zero counts. This is acceptable — the widget handles zero data gracefully.

### Previous Story Intelligence

- **Environment variable pattern:** The project uses `pydantic_settings.BaseSettings` in `backend/common/config.py` with `AliasChoices` for env var mapping. PostHog settings must follow this pattern (added in Task 1). Access via `from common.config import settings` → `settings.posthog_api_key`.
- **Auto-refresh pattern:** No precedent in existing hooks. Implement with `useEffect` + `setInterval`. Consider using a custom `useInterval` hook for cleaner cleanup.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7, Story 7.4] AC definitions
- [Source: _bmad-output/planning-artifacts/epics.md#FR28] Owner can view PostHog visitor count from previous day
- [Source: _bmad-output/planning-artifacts/epics.md#NFR3] PostHog events visible in dashboard: ≤ 10 minutes
- [Source: https://posthog.com/docs/api/queries] PostHog Query API — HogQLQuery kind, rate limits
- [Source: https://posthog.com/tutorials/api-get-insights-persons] PostHog API tutorial — auth, response format

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (via GitHub Copilot)

### Completion Notes List

- Story created after researching PostHog Query API docs via Context7 and web search
- Backend proxy pattern chosen to keep PostHog API key server-side only
- HogQLQuery is the recommended query kind per PostHog docs (insights API deprecated for querying)
- Auto-refresh interval set to 5 minutes — well within PostHog rate limits
- Timezone handling noted: use UTC date for PostHog query consistency
