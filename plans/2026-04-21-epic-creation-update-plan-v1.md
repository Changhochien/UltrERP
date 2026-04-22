# Epic Creation and Update Implementation Plan

## Objective

Create Epic 33 (HR Foundation) and Epic 38 (Taiwan Localization Plus), and update existing epics 23, 27, 28, and 29 with new stories based on the gap analysis report.

## Project Structure Summary

- **Source:** Gap analysis at `plans/2026-04-21-UltrERP-ERPNext-Comprehensive-Gap-Analysis-v1.md`
- **Existing Epics:** `_bmad-output/planning-artifacts/epic-{23,24-32}.md`
- **Output Directory:** `_bmad-output/planning-artifacts/`
- **Main Index:** `_bmad-output/planning-artifacts/epics.md`

## Files to Create

1. **epic-33.md** - HR Foundation (NEW)
2. **epic-38.md** - Taiwan Localization Plus (NEW)

## Files to Update

3. **epic-23.md** - Add Stories 23.6, 23.7, 23.8
4. **epic-27.md** - Replace Story 27.5, add Stories 27.6, 27.7 (existing 27.5 conflicts)
5. **epic-28.md** - Add Stories 28.6, 28.7, 28.8
6. **epic-29.md** - Add Stories 29.6, 29.7, 29.8
7. **epics.md** - Add entries for Epic 33 and Epic 38

## Implementation Plan

- [ ] Task 1: Read all existing epic files to understand structure
- [ ] Task 2: Create epic-33.md following existing format (4 stories: 33.1-33.4)
- [ ] Task 3: Create epic-38.md following existing format (4 stories: 38.1-38.4)
- [ ] Task 4: Update epic-23.md - append Stories 23.6, 23.7, 23.8
- [ ] Task 5: Update epic-27.md - replace Story 27.5, add 27.6, 27.7
- [ ] Task 6: Update epic-28.md - append Stories 28.6, 28.7, 28.8
- [ ] Task 7: Update epic-29.md - append Stories 29.6, 29.7, 29.8
- [ ] Task 8: Update epics.md - add Epic 33 and Epic 38 to index

## Story Details

### Epic 33: HR Foundation
| Story | Title | Description |
|-------|-------|-------------|
| 33.1 | Employee CRUD with department, designation | Employee records with org structure |
| 33.2 | Holiday list with Taiwan holidays | Taiwan-specific holiday calendar |
| 33.3 | Leave management (annual, sick) | Basic leave tracking |
| 33.4 | Attendance tracking | Clock in/out functionality |

### Epic 38: Taiwan Localization Plus
| Story | Title | Description |
|-------|-------|-------------|
| 38.1 | LINE Pay integration | LINE Pay payment gateway |
| 38.2 | ECPay integration | Taiwan e-commerce payment gateway |
| 38.3 | Taiwan banking reconciliation | Local bank statement import/matching |
| 38.4 | Taiwan logistics API | Optional logistics provider integration |

### Updates to Epic 23 (CRM)
| Story | Title | Description |
|-------|-------|-------------|
| 23.6 | UTM Tracking | Marketing attribution on leads/opportunities |
| 23.7 | Lead Conversion | Full lead → Customer workflow |
| 23.8 | CRM Reporting | Pipeline dashboards, win/loss analysis |

### Updates to Epic 27 (Manufacturing)
| Story | Title | Description |
|-------|-------|-------------|
| 27.5 | Routing & Workstation | Operations with cost and capacity |
| 27.6 | Production Plan | Aggregate demand planning |
| 27.7 | Downtime & OEE | Equipment effectiveness tracking |

### Updates to Epic 28 (Workforce)
| Story | Title | Description |
|-------|-------|-------------|
| 28.6 | NCR & CAPA | Non-conformance and corrective action |
| 28.7 | Quality Procedure | Quality procedure tree management |
| 28.8 | Quality Goals & Meetings | Quality objectives and reviews |

### Updates to Epic 29 (Quality Control)
| Story | Title | Description |
|-------|-------|-------------|
| 29.6 | AQL Sampling | Taiwan-specific QC sampling |
| 29.7 | SPC Charts | Statistical process control |
| 29.8 | Supplier Quality Scorecard | Vendor quality scorecard |

## Key Constraints

1. **Epic 27 Story 27.5 Conflict:** Existing epic-27.md has Story 27.5 titled "Advanced Routing Extension Point". Gap analysis recommends Story 27.5 "Routing & Workstation". Will merge the existing "extension point" concept into a proper routing implementation story.

2. **Format Consistency:** All new stories must follow the existing epic format with:
   - Story title as H2 header
   - Story description as bullet points
   - **Acceptance Criteria:** section with Given/When/Then format

3. **File Paths:** All output files go to `_bmad-output/planning-artifacts/`

## Verification Criteria

- [ ] Epic 33 file created with 4 complete stories
- [ ] Epic 38 file created with 4 complete stories
- [ ] Epic 23 updated with 3 new stories (total 8 stories)
- [ ] Epic 27 updated with 3 new stories (total 8 stories)
- [ ] Epic 28 updated with 3 new stories (total 8 stories)
- [ ] Epic 29 updated with 3 new stories (total 8 stories)
- [ ] epics.md index updated with new epic entries
- [ ] All stories have proper acceptance criteria
- [ ] All new epics have complete sections (Goal, Business Value, Scope, Non-Goals, Technical Approach, Key Constraints, Dependency and Phase Order)
