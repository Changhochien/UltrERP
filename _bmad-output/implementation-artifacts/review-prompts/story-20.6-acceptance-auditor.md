Use the acceptance-auditor prompt from the `bmad-code-review` workflow.

Review target:

- Repository: `/Volumes/2T_SSD_App/Projects/UltrERP`
- Commit: `3b2054b`
- Title: `Complete Story 20.6 product performance API`
- Spec/story file: `/Volumes/2T_SSD_App/Projects/UltrERP/_bmad-output/implementation-artifacts/20-6-product-performance-api.md`

Primary diff command:

```bash
cd /Volumes/2T_SSD_App/Projects/UltrERP && git show --format=medium 3b2054b --
```

Context docs to load if useful:

- `/Volumes/2T_SSD_App/Projects/UltrERP/_bmad-output/planning-artifacts/epic-20.md`
- `/Volumes/2T_SSD_App/Projects/UltrERP/_bmad-output/planning-artifacts/research/domain-epic-20-product-sales-analytics-research-2026-04-15.md`

Audit instructions:

Review this diff against the spec and context docs. Check for:

- violations of acceptance criteria
- deviations from spec intent
- missing implementation of specified behavior
- contradictions between spec constraints and actual code

Output findings as a Markdown list.

For each finding include:

- one-line title
- which AC or constraint it violates
- evidence from the diff

If there are no actionable findings, return exactly: `No actionable findings.`