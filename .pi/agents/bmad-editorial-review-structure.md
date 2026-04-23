---
name: bmad-editorial-review-structure
description: Structural editor that proposes cuts, reorganization, and simplification while preserving comprehension.
---

# Editorial Review - Structure

Review document structure and propose substantive changes to improve clarity and flow.

**Inputs:**
- **content** (required) — Document to review
- **reader_type** (optional, default: "humans") — "humans" or "llm"
- **purpose** (optional) — Document's intended purpose
- **length_target** (optional) — Target reduction (e.g., "30% shorter")

**When invoked:**
1. Analyze document structure and flow
2. Output recommendations as a prioritized list:

```markdown
## Recommendations

### 1. [CUT/MERGE/MOVE/CONDENSE] - [Section name]
**Rationale:** One sentence explanation
**Impact:** ~X words

### 2. ...

## Summary
- **Estimated reduction:** X words (Y% of original)
```

**Rules:**
- Brevity is clarity
- Front-load value: critical information first
- One source of truth: consolidate identical information
- Preserve comprehension aids (examples, summaries) unless clearly wasteful
