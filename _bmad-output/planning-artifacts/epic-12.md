## Epic 12: Desktop Shell & Tray

### Epic Goal

Users can run the app from system tray with keyboard shortcuts and background notifications.

### Stories

### Story 12.1: Virtualized Lists for 5,000+ Rows

As a user,
I want customer and inventory lists to remain responsive with 5,000+ rows,
So that I don't experience lag when browsing large datasets.

**Acceptance Criteria:**

**Given** I'm viewing a list with 5,000+ items
**When** I scroll through the list
**Then** there is no visible stutter or lag
**And** list renders within 2 seconds (p95)

### Story 12.2: Keyboard Shortcuts with Overlay

As a power user,
I want to access primary screens and actions through global keyboard shortcuts plus a screen-local shortcut overlay,
So that I can work efficiently without mouse.

**Acceptance Criteria:**

**Given** I'm using the app
**When** I press `?` or `Ctrl+/`
**Then** the shortcut overlay appears showing all available shortcuts
**And** global shortcuts work across the app
**And** shortcuts are discoverable and documented

### Story 12.3: eGUI Status Badge and State Persistence

As a user,
I want invoice screen to show async eGUI status badge, deadline awareness, and persisted state,
So that I can track invoice submissions.

**Acceptance Criteria:**

**Given** eGUI is enabled for the tenant
**When** I view an invoice
**Then** I see an async status badge (PENDING, QUEUED, SENT, ACKED, FAILED)
**And** I see deadline awareness for submission windows
**And** I can manually refresh status
**And** state persists across app restarts

### Story 12.4: System Tray Mode with Notifications

As a user,
I want the desktop app to run in system tray and send notifications,
So that I can monitor async operations while the main window is closed.

**Acceptance Criteria:**

**Given** the app is running
**When** I close the main window
**Then** the app continues running in system tray
**And** I receive desktop notifications for async invoice/eGUI state changes
**And** clicking the tray icon restores the main window

### Story 12.5: Print Preview Performance

As a finance clerk,
I want invoice print preview to render in < 1 second,
So that I can quickly review before printing.

**Acceptance Criteria:**

**Given** an invoice exists
**When** I click preview
**Then** the print preview renders in < 1 second

---

