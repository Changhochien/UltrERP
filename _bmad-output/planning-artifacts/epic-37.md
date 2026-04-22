# Epic 37: Integration and Automation Platform

## Epic Goal

Add a first-class integration platform that enables external systems to receive real-time event notifications via webhooks, supports customizable email templates for communications, provides a unified global search across all document types, and offers scheduled job management for background automation — transforming UltrERP from an isolated ERP into a connected business platform.

## Business Value

- External systems (e-commerce, logistics, accounting) receive real-time notifications when business events occur.
- Email communications maintain consistent branding through customizable templates.
- Users find data faster through unified search across all modules.
- Background jobs run reliably on schedule without manual intervention.
- IT teams can build integrations without modifying ERP source code.
- UltrERP gains ERPNext-equivalent integration capabilities and exceeds them with modern async architecture.

## Scope

**Backend:**
- Webhook definition and delivery system with retry logic.
- Event bus for document lifecycle events (created, updated, submitted, cancelled).
- Email template engine with variable substitution.
- Global search index with full-text search across document types.
- Background job scheduler with monitoring.

**Frontend:**
- Webhook configuration UI with event selection and payload preview.
- Email template builder with preview.
- Global search interface with type-ahead.
- Scheduled job management dashboard.

**Data Model:**
- `Webhook` — name, url, events[], secret, headers, is_active, retry_policy.
- `WebhookDelivery` — webhook_id, event, payload, status, attempts, last_error, delivered_at.
- `EmailTemplate` — name, subject, body_html, body_text, variables[].
- `ScheduledJob` — name, job_type, schedule, last_run, next_run, status, config_json.
- `SearchIndex` — document_type, document_id, content, indexed_at.

## Non-Goals

- Real-time streaming (Server-Sent Events or WebSocket) — HTTP webhooks only in v1.
- Workflow automation engine (see Epic 35).
- Visual flow builder for integrations.
- Third-party integration marketplace.
- GraphQL API (REST-only for v1).

## Technical Approach

- Treat webhooks as fire-and-forget with reliable retry using exponential backoff.
- Implement event bus as an in-process event emitter; extend to message queue later.
- Use Jinja2 for email template rendering.
- Build search index using PostgreSQL full-text search (no external search engine for v1).
- Use APScheduler or similar for background job scheduling.
- All webhook payloads are signed with HMAC-SHA256 for verification.

## Key Constraints

- Webhook delivery must not block the main request; use async processing.
- Email templates must not allow arbitrary Python execution.
- Global search must respect RBAC (users only see what they can access).
- Background jobs must be idempotent and recoverable.
- Epic 26 (GL) is a prerequisite for accounting event webhooks.
- Epic 22 (UI Foundation) is a prerequisite for webhook/email UI.

## Dependency and Phase Order

1. Webhook core (Stories 37.1-37.3) can land early; minimal dependencies.
2. Email templates (Story 37.4) depends on notification channels from Epic 6.
3. Global search (Story 37.5) depends on document models being stable (post Epics 21-32).
4. Job scheduler (Story 37.6) can land independently.
5. Epic 37 can proceed in parallel with Epics 21-32 once foundational models exist.

---

## Story 37.1: Webhook Definition and Event System

- Add `Webhook` records with: name, URL, subscribed events, secret key, custom headers.
- Define event types: `document.created`, `document.updated`, `document.submitted`, `document.cancelled` per document type.
- Register webhook URLs per event type.
- Validate webhook URL format and test connectivity on save.
- Support webhook disabling without deletion.
- Implement webhook secret rotation.

**Acceptance Criteria:**

- Given a webhook is created for `order.confirmed`
- When an order is confirmed
- Then a webhook delivery is queued with the order event payload

- Given a webhook URL is unreachable during creation
- When the admin saves the webhook
- Then the system warns but allows saving (connectivity test is advisory)

- Given a webhook is disabled
- When events fire
- Then no deliveries are attempted for that webhook

---

## Story 37.2: Webhook Delivery Engine and Retry Logic

- Implement async webhook delivery using background worker.
- Sign payloads with HMAC-SHA256 using the webhook secret.
- Implement retry policy: 3 attempts with exponential backoff (1min, 5min, 15min).
- Track delivery status: pending, success, failed, retrying.
- Store delivery attempts and error messages for debugging.
- Support manual retry from admin UI.
- Implement dead-letter queue for permanently failed webhooks.

**Acceptance Criteria:**

- Given an event fires for a registered webhook
- When the delivery is attempted
- Then the payload is signed with HMAC-SHA256 and POSTed to the URL

- Given a webhook delivery fails
- When retry conditions are met
- Then the delivery is retried with exponential backoff

- Given a webhook delivery fails all retries
- When the retry limit is reached
- Then the delivery is marked as failed and the admin is notified

- Given an admin views a webhook delivery
- When they see a failed attempt
- Then they can manually retry with a single click

---

## Story 37.3: Webhook Admin UI and Testing

- Add webhook configuration workspace for administrators.
- List all webhooks with status indicators (active, disabled, failing).
- Event selector: choose which document events trigger the webhook.
- Payload preview: show sample payload for selected event.
- Delivery log viewer: search and filter deliveries by status, event, date.
- Test webhook button: send sample payload to verify URL receives it.
- Webhook statistics: success rate, average latency, failure reasons.

**Acceptance Criteria:**

- Given an admin opens the webhook configuration
- When they select an event type
- Then the payload preview shows the structure and sample data

- Given an admin clicks "Test Webhook"
- When the test executes
- Then a delivery is sent with test payload and result is displayed

- Given an admin views the delivery log
- When they filter by failed status
- Then all failed deliveries are shown with error details

---

## Story 37.4: Email Template Engine

- Add `EmailTemplate` records with: name, subject, body_html, body_text, variables.
- Support variable substitution: `{{customer.name}}`, `{{order.number}}`, `{{user.email}}`.
- Provide default templates for common communications (welcome, order confirmation, invoice, payment receipt).
- HTML template editor with preview.
- Text fallback for email clients that don't support HTML.
- Template versioning and rollback.
- Link email templates to notification events.

**Acceptance Criteria:**

- Given an email template is created with variables
- When it is rendered for a specific document
- Then all variables are substituted with actual values

- Given an email template is previewed
- When the preview loads
- Then it shows the rendered email with sample data

- Given a user receives an email from the system
- When they view the plain text version
- Then it contains the same content as the HTML version

---

## Story 37.5: Global Search

- Implement full-text search across all searchable document types.
- Build search index on document create/update.
- Support search operators: phrase, prefix, fuzzy, wildcard.
- Filter search by document type, date range, status.
- Respect RBAC: search results filtered by user permissions.
- Implement search suggestions (type-ahead) based on recent searches.
- Rank results by relevance and recency.
- Support search across custom fields (Epic 36).

**Acceptance Criteria:**

- Given a user types a search query
- When they type in the global search box
- Then search suggestions appear based on partial matches

- Given a user searches for a document
- When the results load
- Then they are ranked by relevance and filtered by user permissions

- Given a user filters search by document type
- When the filter is applied
- Then only documents of that type are returned

- Given a new document is created
- When it is saved
- Then it appears in search results within 30 seconds

---

## Story 37.6: Background Job Scheduler and Monitoring

- Add `ScheduledJob` records with: name, job_type, schedule (cron expression), handler, config.
- Support job types: webhook_digest, report_generation, data_cleanup, sync_external.
- Implement job scheduler using APScheduler or similar.
- Track job execution: start_time, end_time, status, output, errors.
- Implement job concurrency limits (prevent overlapping runs).
- Support job pausing and resuming.
- Alert on job failures (Epic 6 notification channels).
- Job dashboard: view all scheduled jobs, execution history, next run time.

**Acceptance Criteria:**

- Given a scheduled job is configured
- When the scheduled time arrives
- Then the job executes automatically

- Given a job is currently running
- When another scheduled trigger arrives
- Then the second run is skipped (concurrency limit)

- Given a job fails during execution
- When the failure occurs
- Then the error is logged and an alert is sent

- Given an admin views the job dashboard
- When they see job execution history
- Then they can see start time, end time, status, and errors for each run

---

## Story 37.7: API Rate Limiting and Quota Management

- Implement rate limiting for external API consumers.
- Define rate limit tiers: free (100/hour), standard (1000/hour), enterprise (10000/hour).
- Track API usage per consumer key.
- Return rate limit headers in API responses: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
- Implement quota alerts when approaching limits.
- Support quota overrides for specific consumers.
- Document rate limiting in API documentation.

**Acceptance Criteria:**

- Given an API consumer exceeds their rate limit
- When they make another request
- Then they receive a 429 Too Many Requests response

- Given an API consumer is approaching their quota
- When they reach 80% of the limit
- Then they receive a warning notification

- Given an admin reviews API usage
- When they see a consumer exceeding limits
- Then they can adjust the quota or revoke the key

---

## Story 37.8: Webhook and Integration Audit Logging

- Log all webhook deliveries with full request/response context.
- Log all API authentication attempts (success and failure).
- Log all scheduled job executions.
- Log email template renders and delivery status.
- Support log retention policies (configurable per data type).
- Export audit logs for compliance reporting.
- Integrate with existing audit log infrastructure (Epic 11).

**Acceptance Criteria:**

- Given an auditor reviews webhook delivery logs
- When they query for a specific webhook ID
- Then they see all delivery attempts with request payloads and response codes

- Given an audit requires API authentication logs
- When the logs are exported
- Then they include: timestamp, API key (masked), endpoint, status, IP address

- Given log retention is configured for 90 days
- When older logs are queried
- Then they are not available (respecting retention policy)
