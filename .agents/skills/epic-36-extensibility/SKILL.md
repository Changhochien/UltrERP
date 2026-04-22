---
name: epic-36-extensibility
description: Implementation guide for Epic 36 extensibility - custom fields, file attachments, print formats, import/export, and document versioning.
location: /Users/changtom/Downloads/UltrERP/.agents/skills/epic-36-extensibility/SKILL.md
---

# Epic 36: Extensibility and Document Management

## Overview

Epic 36 adds no-code extensibility with custom fields, file attachments, print format builder, data import/export, and document versioning.

## Stories

- **36.1**: Custom Field Definition Model
- **36.2**: Custom Field Builder Admin UI
- **36.3**: File Attachment Storage and Management
- **36.4**: Print Format Templates
- **36.5**: Data Import and Export
- **36.6**: Document Versioning and Change Tracking
- **36.7**: Dashboard and Analytics for Customizations

## Key Features

- Custom field builder for any document
- S3/MinIO file attachment storage
- Jinja-based print templates
- CSV/JSON import/export with field mapping
- Document version history with SCD Type 2

## Documentation

- Epic spec: `_bmad-output/planning-artifacts/epic-36.md`
- Stories: `_bmad-output/implementation-artifacts/story-36-*.md`

## Usage

When implementing Epic 36 stories:

```
"dev story 36.1" → bmad-dev-story
"implement custom fields" → bmad-dev-story
"create print formats" → bmad-dev-story
```
