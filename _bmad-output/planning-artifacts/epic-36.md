# Epic 36: Extensibility and Document Management

## Epic Goal

Add a no-code extensibility layer that allows administrators to extend document schemas with custom fields, attach files to records, manage print formats, and import/export data — enabling UltrERP to adapt to diverse business requirements without developer intervention.

## Business Value

- Administrators can add custom fields to any document without code changes.
- File attachments become first-class record artifacts with versioning.
- Print formats can be customized for different business needs.
- Data import/export enables integration with external systems.
- Document versioning tracks change history for audit compliance.
- UltrERP gains ERPNext-equivalent customization capabilities.

## Scope

**Backend:**
- Custom field definitions and dynamic schema extension.
- File attachment storage with S3/MinIO backend.
- Print format templates (HTML/Jinja).
- Data import/export with field mapping.
- Document version history.

**Frontend:**
- Custom field builder UI for administrators.
- File upload/download UI on document forms.
- Print format preview and selection.
- Import wizard with field mapping.
- Version history viewer on documents.

**Data Model:**
- `CustomField` — document_type, field_name, label, field_type, options, required, default.
- `FileAttachment` — document_type, document_id, file_name, file_key, mime_type, size, uploaded_by.
- `PrintFormat` — name, document_type, html_template, is_default.
- `DocumentVersion` — document_type, document_id, version, changed_by, changed_at, changes_json.

## Non-Goals

- Custom field validation expressions (v1 uses simple required/default only).
- Dynamic document type creation (only extend existing types).
- Advanced print format designer (HTML editing only).
- Real-time collaborative editing.
- Full-featured document management (sharepoint-equivalent).

## Technical Approach

- Store custom field definitions in a dedicated table; apply at API layer before read/write.
- Use existing object store (MinIO/S3) for file attachments with presigned URLs.
- Implement print formats as Jinja templates rendered server-side.
- Use bulk CSV/JSON for import/export with configurable field mapping.
- Implement SCD Type 2 for document versions when enabled.

## Key Constraints

- Custom fields must not break existing API contracts; use optional fields.
- Print format templates must not allow arbitrary Python execution.
- Import must support rollback on validation failure.
- Epic 22 (UI Foundation) is a prerequisite for custom field UI.
- File attachments must integrate with existing object store (Epic 2).

## Dependency and Phase Order

1. Custom field model (Story 36.1) lands before UI builder (Story 36.2).
2. File attachment storage (Story 36.3) depends on Epic 2 storage setup.
3. Print formats (Story 36.4) lands after custom fields are stable.
4. Import/Export (Story 36.5) can land independently.
5. Document versioning (Story 36.6) lands last as audit enhancement.
6. Epic 36 can proceed in parallel with Epics 21-32.

---

## Story 36.1: Custom Field Definition Model

- Add `CustomField` records with: document_type, field_name, label, field_type, options, required, default_value, depends_on.
- Support field types: Text, Number, Date, Select, MultiSelect, Checkbox, Link, Currency, Percent.
- Validate custom field definitions: no duplicate names, valid field types, safe names (alphanumeric + underscore only).
- Apply custom fields to document schemas at read/write time.
- Custom fields are optional unless marked required.
- Support field ordering and grouping (section break, column break).

**Acceptance Criteria:**

- Given a custom field is created for a document type
- When a document of that type is loaded via API
- Then the custom field is included in the response

- Given a custom field is marked required
- When a document is saved without that field
- Then validation fails with a clear error

- Given a custom field references a Link type
- When the linked document type is queried
- Then the custom field supports autocomplete and validation

---

## Story 36.2: Custom Field Builder Admin UI

- Add custom field workspace for administrators.
- Form builder: select document type, add fields, configure properties.
- Field type selector with preview for each type.
- Drag-and-drop field ordering.
- Field grouping with section/column breaks.
- Preview custom field form before saving.
- Enable/disable custom fields without deletion.

**Acceptance Criteria:**

- Given an admin opens the custom field builder
- When they select a document type
- Then the builder shows existing and custom fields for that type

- Given an admin adds a new field
- When they configure field type and options
- Then the preview updates to show the field

- Given a custom field form is rendered
- When it is displayed
- Then custom fields appear inline with standard fields in the configured order

---

## Story 36.3: File Attachment Storage and Management

- Add `FileAttachment` model: document_type, document_id, file_name, file_key, mime_type, size, uploaded_by, uploaded_at.
- Integrate with existing object store (MinIO/S3) for file storage.
- Generate presigned URLs for secure upload/download.
- Support file versioning: same key stores multiple versions.
- Link attachments to document records.
- Support file type restrictions per document type.
- Implement file size limits and quota per tenant.

**Acceptance Criteria:**

- Given a user uploads a file to a document
- When the upload completes
- Then the file is stored in object store and linked to the document

- Given a user downloads a file attachment
- When the download is requested
- Then a presigned URL is generated with appropriate expiration

- Given an admin sets file type restrictions
- When a user attempts to upload a disallowed file type
- Then the upload is rejected with a clear error

---

## Story 36.4: Print Format Templates

- Add `PrintFormat` model: name, document_type, html_template, css, is_default, created_by.
- Implement print format as Jinja2 templates with document context.
- Support standard document fields and custom fields in templates.
- Provide template variables: `document`, `lines`, `company`, `config`.
- Add default print formats for core document types.
- Preview print format before activation.
- Allow multiple print formats per document type; user selects at print time.

**Acceptance Criteria:**

- Given a print format template is created
- When it is rendered for a document
- Then all document fields are available in the template context

- Given a print format is previewed
- When the preview loads
- Then it shows an accurate representation of the print output

- Given a user prints a document
- When multiple print formats exist
- Then they can select which format to use

---

## Story 36.5: Data Import and Export

- Add import wizard: select file (CSV/JSON), map fields, validate, preview, import.
- Field mapping UI: source column to target field with transformation options.
- Validation rules: required fields, data types, unique constraints.
- Preview import results before committing.
- Support rollback on import failure (transaction-based).
- Export documents to CSV/JSON with field selection.
- Batch export with filters and pagination.

**Acceptance Criteria:**

- Given a user imports a CSV file
- When field mapping is configured
- Then the preview shows the mapped data with validation results

- Given an import has validation errors
- When the user reviews errors
- Then they can fix errors in the source file or adjust mappings

- Given an import is executed
- When it fails mid-way
- Then the transaction is rolled back and no partial data is imported

- Given a user exports documents
- When they select fields and filters
- Then the export file contains only the selected data

---

## Story 36.6: Document Versioning and Change Tracking

- Add `DocumentVersion` model: document_type, document_id, version, changed_by, changed_at, changes_json, snapshot.
- Enable versioning per document type (opt-in).
- Create version snapshot on significant state changes (submit, cancel, approve).
- Store before/after field values as JSON diff.
- Retrieve document at any historical version.
- Compare two versions side-by-side.
- Limit version history retention (configurable, default 90 days for non-invoice documents).

**Acceptance Criteria:**

- Given a document is submitted with versioning enabled
- When the submission succeeds
- Then a new version snapshot is created with the current state

- Given a user views document version history
- When they select a previous version
- Then the document is displayed as it was at that point in time

- Given a user compares two versions
- When the comparison is generated
- Then it shows fields that changed with before/after values

---

## Story 36.7: Dashboard and Analytics for Customizations

- Add customization dashboard: custom field usage, print format usage, attachment storage.
- Track which custom fields are actively used.
- Monitor attachment storage usage per tenant.
- Report on import/export activity.
- Alert on custom field usage anomalies (unused fields, field causing validation errors).

**Acceptance Criteria:**

- Given an admin views the customization dashboard
- When they see custom field usage
- Then they can identify fields with low or no usage for cleanup

- Given storage quota is approaching
- When attachments are uploaded
- Then the system alerts the admin and users

- Given import activity is monitored
- When success/failure rates are analyzed
- Then the admin can identify common import errors for training
