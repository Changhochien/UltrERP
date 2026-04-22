---
name: epic-35-workflow
description: Implementation guide for Epic 35 workflow automation engine - workflow definitions, state machine, transitions, notifications, and admin UI.
location: /Users/changtom/Downloads/UltrERP/.agents/skills/epic-35-workflow/SKILL.md
---

# Epic 35: Workflow Automation Engine

## Overview

Epic 35 adds a generic workflow engine for custom approval chains, document state transitions, and automated notifications without code changes.

## Stories

- **35.1**: Workflow Definition Model and State Machine
- **35.2**: Workflow Engine Core and Transition Evaluation
- **35.3**: Document Workflow State Integration
- **35.4**: Workflow Notifications and Alerts
- **35.5**: Workflow Builder Admin UI
- **35.6**: Workflow Audit Trail and Reporting

## Key Features

- Visual workflow builder
- State machine with conditional transitions
- Role-based action permissions
- Notification triggers on state changes
- Workflow history and audit trail

## Documentation

- Epic spec: `_bmad-output/planning-artifacts/epic-35.md`
- Stories: `_bmad-output/implementation-artifacts/story-35-*.md`

## Usage

When implementing Epic 35 stories:

```
"dev story 35.1" → bmad-dev-story
"implement workflow" → bmad-dev-story
"create workflow engine" → bmad-dev-story
```
