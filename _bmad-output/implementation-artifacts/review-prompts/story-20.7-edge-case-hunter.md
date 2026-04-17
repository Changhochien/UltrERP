Use the `bmad-review-edge-case-hunter` skill.

Review target:

- Repository: `/Volumes/2T_SSD_App/Projects/UltrERP`
- Commit: `74c0d1f`
- Title: `Complete Story 20.7 customer buying behavior`

Inputs:

- `content`: the diff from the command below
- `also_consider`: customer_type cohort boundaries, outside-segment lift baseline behavior, partial-window handling, deterministic tie ordering, and empty-state handling

Command to inspect:

```bash
cd /Volumes/2T_SSD_App/Projects/UltrERP && git show --format=medium 74c0d1f --
```

Scope rules:

- Walk only reachable branch and boundary conditions from the diff.
- Project read access is allowed for spot checks, but findings must remain directly tied to changed lines.

Output format:

- Return only the JSON array required by the skill
- If there are no actionable findings, return `[]`