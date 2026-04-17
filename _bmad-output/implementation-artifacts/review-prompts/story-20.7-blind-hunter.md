Use the `bmad-review-adversarial-general` skill.

Review target:

- Repository: `/Volumes/2T_SSD_App/Projects/UltrERP`
- Commit: `74c0d1f`
- Title: `Complete Story 20.7 customer buying behavior`

Scope rules:

- Review the commit diff only.
- Do not load the story file.
- Do not inspect surrounding project files unless the diff itself is unreadable.
- Treat this as a blind adversarial diff review.

Command to inspect:

```bash
cd /Volumes/2T_SSD_App/Projects/UltrERP && git show --format=medium 74c0d1f --
```

Review focus:

- Bugs
- Behavioral regressions
- Contract mismatches visible from the diff
- Missing validation or error handling
- Missing tests for changed behavior

Output format:

- Markdown list of findings only
- Order by severity
- If there are no actionable findings, return exactly: `No actionable findings.`

For each finding include:

- severity
- concise title
- file path
- line number or nearest symbol
- explanation
- why it matters