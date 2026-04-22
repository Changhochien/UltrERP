---
name: epic-37-integration
description: Implementation guide for Epic 37 integration platform - webhooks, email templates, global search, job scheduler, and rate limiting.
location: /Users/changtom/Downloads/UltrERP/.agents/skills/epic-37-integration/SKILL.md
---

# Epic 37: Integration and Automation Platform

## Overview

Epic 37 adds webhooks, email templates, global search, background job scheduler, rate limiting, and integration audit logging.

## Stories

- **37.1**: Webhook Definition and Event System
- **37.2**: Webhook Delivery Engine and Retry Logic
- **37.3**: Webhook Admin UI and Testing
- **37.4**: Email Template Engine
- **37.5**: Global Search
- **37.6**: Background Job Scheduler and Monitoring
- **37.7**: API Rate Limiting and Quota Management
- **37.8**: Webhook and Integration Audit Logging

## Key Features

- Webhook delivery with exponential backoff retry
- HMAC-SHA256 signed payloads
- Jinja email templates with variable substitution
- PostgreSQL full-text search
- APScheduler-based job management
- Rate limiting per API consumer

## Documentation

- Epic spec: `_bmad-output/planning-artifacts/epic-37.md`
- Stories: `_bmad-output/implementation-artifacts/story-37-*.md`

## Usage

When implementing Epic 37 stories:

```
"dev story 37.1" → bmad-dev-story
"implement webhooks" → bmad-dev-story
"create global search" → bmad-dev-story
```
