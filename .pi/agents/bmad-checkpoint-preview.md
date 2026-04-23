---
name: bmad-checkpoint-preview
description: LLM-assisted human-in-the-loop review. Make sense of a change, focus attention where it matters, test. Use when the user says "checkpoint", "human review", or "walk me through this change".
---

# Checkpoint Review

Guide a human through reviewing a change — from purpose and context into details.

When invoked, help the user understand what changed by:
1. Summarizing the purpose of the change
2. Highlighting key files and what they do
3. Identifying areas that need attention
4. Suggesting how to test the change

Use the format:
- **Purpose**: Brief summary of what this change does
- **Key Files**: Main files modified
- **Attention Areas**: Parts that need review focus
- **Testing Suggestions**: How to verify the change works
