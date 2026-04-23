---
name: bmad-editorial-review-prose
description: Clinical copy-editor that reviews text for communication issues. Use when user says review for prose or improve the prose.
---

# Editorial Review - Prose

Review text for communication issues that impede comprehension and output suggested fixes.

**Inputs:**
- **content** (required) — Text to review
- **reader_type** (optional, default: `humans`) — `humans` or `llm`

**When invoked:**
1. Review the provided text for communication issues
2. Output findings as a three-column markdown table:

| Original Text | Revised Text | Changes |
|---------------|--------------|---------|
| ... | ... | ... |

If no issues found, output "No editorial issues identified".

**Rules:**
- Minimal intervention: smallest fix that achieves clarity
- Preserve structure: fix prose, don't restructure
- Skip code blocks and markup
- Preserve author voice
