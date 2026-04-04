# Story 2.5: Archive MIG 4.1 XML in MinIO

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a system,
I want to store issuer-side invoice artifacts in MinIO,
so that we have durable archives independent of MOF platform retention.

## Acceptance Criteria

1. Given an invoice is issued, when artifact generation runs, then the system generates schema-valid MIG 4.1 XML for that invoice from the persisted snapshot and stores it in MinIO at `{tenant_id}/mig41/{invoice_id}.xml`.
2. Given the artifact is stored successfully, when the invoice record is read later, then an `invoice_artifacts` record stores the object key, checksum, content type, retention metadata, and storage-policy metadata as the system of record.
3. Given invoice artifacts are archived, when retention expectations are evaluated, then the system treats issuer-side storage as the primary archive, records a 10+ year retention baseline in metadata, and uses immutable-storage controls where the target environment supports them.
4. Given local development or CI runs without immutable bucket controls, when tests execute, then the story still verifies upload/download behavior and metadata persistence through a documented MinIO/Testcontainers or S3-compatible mock strategy.

## Tasks / Subtasks

- [ ] Task 1: Add invoice artifact persistence structures (AC: 1, 2, 3)
  - [ ] Create an `invoice_artifacts` table linked to invoices with fields for `tenant_id`, `invoice_id`, `artifact_kind`, `object_key`, `content_type`, `checksum_sha256`, `byte_size`, `retention_class`, `retention_until`, `storage_policy`, and `created_at`.
  - [ ] Store artifact kind, object key, content type, created timestamp, checksum, and retention-relevant metadata.
  - [ ] Ensure invoice artifact records carry `tenant_id` and link back to the invoice aggregate.
- [ ] Task 2: Implement MIG 4.1 XML generation from invoice data (AC: 1)
  - [ ] Add a generator module such as `backend/domains/invoices/mig41.py` or `backend/domains/invoices/artifacts.py`.
  - [ ] Reuse the MIG 4.1 field rules already validated in research and PoC work; do not reintroduce MIG 4.0 assumptions.
  - [ ] Validate B2B versus B2C buyer identifiers, summary and detail `TaxType`, and integer amount fields before upload.
  - [ ] Generate XML from persisted invoice data, not from transient UI payloads.
- [ ] Task 3: Implement MinIO/S3-compatible storage adapter (AC: 1, 2, 3, 4)
  - [ ] Create an object-storage adapter under `backend/common/` such as `backend/common/object_store.py`.
  - [ ] Support MinIO via S3-compatible APIs and object keys following `{tenant_id}/mig41/{invoice_id}.xml`.
  - [ ] Document the capability split between production storage, which should enable immutable-retention controls where supported, and local dev/test storage, which may omit long-horizon lock enforcement while still validating object semantics.
  - [ ] Keep the storage interface reusable for future attachment artifacts.
- [ ] Task 4: Hook artifact generation into invoice issuance flow (AC: 1, 2)
  - [ ] Trigger XML generation and object-store upload from the `InvoiceIssued` workflow extension point introduced in Story 2.1.
  - [ ] Record storage metadata, checksum, and retention metadata in the same authoritative workflow path so the invoice knows where its archive artifact lives.
  - [ ] Keep FIA submission out of scope; this story archives issuer-side artifacts only.
- [ ] Task 5: Add artifact-storage tests (AC: 1, 2, 3, 4)
  - [ ] Add unit tests for XML generation and object-key formatting.
  - [ ] Add integration tests using MinIO/Testcontainers or an S3-compatible mock to verify upload and metadata persistence.

## Dev Notes

### Story Context

- Story 2.5 depends on Story 2.1 producing complete persisted invoice data and a reliable issuance hook.
- Story 2.5 should consume the shared totals-validation gate from Story 2.4 before generating archival artifacts.
- Story 2.5 precedes live FIA submission concerns; issuer-side archival must work even when eGUI is feature-flagged off.
- Story 2.6 may later add PDF artifacts, but this story is specifically about MIG 4.1 XML archival.

### Dependency Sequencing

- Implement Story 2.5 after Story 2.1 and Story 2.4.
- Prefer Story 2.5 after Story 2.7 so archival begins after immutable invoice-content rules are enforced.
- Do not wait on Story 2.2 or Story 2.6 for this work; MIG 4.1 XML archival is independent of print/PDF once the invoice state is stable.

### Scope Guardrails

- Do not implement live FIA API calls here.
- Do not make MOF platform availability the archive of record.
- Do not tie artifact storage to only one deployment mode; the interface should remain valid for solo and team configurations.

### Technical Requirements

- Object key format must be `{tenant_id}/mig41/{invoice_id}.xml`.
- XML generation must honor MIG 4.1 line-level tax fields and invoice number formatting.
- Artifact generation should use persisted invoice values and sanctioned invoice-state transitions only.
- Storage adapter should be S3-compatible and MinIO-backed, not MinIO-specific at the domain boundary.
- Artifact metadata must record enough retention and checksum information to support later audit and retrieval workflows.

### Architecture Compliance

- Reuse the architecture's issuer-side archive model and retention baseline.
- Keep object-store plumbing in `backend/common/` and invoice-specific artifact orchestration in `backend/domains/invoices/`.
- Leave later outbox/FIA workflows extensible without coupling this story to external submission.

### Retention and Compliance Notes

- Product and architecture artifacts require core financial records and books to remain available for at least 10 years.
- Invoice artifacts stored here are issuer-side records and must remain exportable independently of MOF platform retention windows.
- The story must record the retention baseline in metadata even if immutable bucket enforcement is configured differently between local, staging, and production environments.

### Testing Requirements

- Mandatory backend coverage:
  - MIG 4.1 XML generation for a valid invoice
  - correct object-key path formatting
  - metadata persistence after upload
  - failure handling when object storage is unavailable
- Use MinIO or an S3-compatible test double in integration coverage.

### Project Structure Notes

- Suggested files:
  - `backend/domains/invoices/mig41.py`
  - `backend/domains/invoices/artifacts.py`
  - `backend/common/object_store.py`
  - `backend/tests/domains/invoices/test_artifacts.py`
  - `backend/tests/integration/test_minio_invoice_artifacts.py`
  - `migrations/versions/*_add_invoice_artifacts.py`

### Risks / Open Questions

- Epic 1 does not provision MinIO on day one for local development. This story now requires a clear local dev/test strategy using MinIO/Testcontainers or a compatible mock.
- Production immutable-retention enforcement still depends on environment provisioning choices such as MinIO Object Lock or equivalent bucket controls; this story must document the selected `storage_policy` rather than assuming one universal mechanism.
- XML generation is supported by existing PoC research, but production mapping of some product/tax edge cases still depends on the tax mapping policy introduced in Story 2.1.

### References

- `_bmad-output/epics.md` — Story 2.5 acceptance criteria and MinIO retention requirements.
- `_bmad-output/planning-artifacts/prd.md` — issuer-side archive expectations and retention baseline.
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` — MinIO usage, `InvoiceIssued` outbox semantics, and retention policy baseline.
- `research/egui-compliance/01-survey-memo.md` — MIG 4.1 XML field requirements.
- `research/egui-compliance/02-poc/` — proven MIG 4.1 XML generator reference.

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `/Users/hcchang/Library/Application Support/Code - Insiders/User/workspaceStorage/4320abfca0ca1465bc6bebe187407283/GitHub.copilot-chat/debug-logs/e9fed657-b634-4e14-91d2-303118396630`

### Completion Notes List

- Story updated to define an explicit `invoice_artifacts` record and environment-aware retention metadata.
- Live FIA submission is explicitly deferred even though the same invoice data shape must remain compatible.
- XML archival now runs from the authoritative invoice issuance workflow and stores returned storage-policy metadata from the object-store adapter.
- Config-backed object-store and archive settings are wired through invoice routes/service, and focused backend pytest plus Ruff validation pass for the archival slice.

### File List

- `backend/domains/invoices/mig41.py`
- `backend/domains/invoices/artifacts.py`
- `backend/domains/invoices/routes.py`
- `backend/domains/invoices/service.py`
- `backend/common/config.py`
- `backend/common/object_store.py`
- `backend/tests/domains/invoices/test_artifacts.py`
- `backend/tests/integration/test_minio_invoice_artifacts.py`
- `migrations/versions/*_add_invoice_artifacts.py`
