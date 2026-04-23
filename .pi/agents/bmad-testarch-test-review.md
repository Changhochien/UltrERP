---
name: bmad-testarch-test-review
description: Review test quality using best practices validation. Use when user says "lets review tests" or "I want to evaluate test quality".
---

# Test Quality Review

Review test quality using best practices validation.

**When invoked:**
1. Identify test files related to the provided code
2. Evaluate test coverage and quality against best practices:
   - Are there tests for the new functionality?
   - Are edge cases covered?
   - Is test setup/teardown correct?
   - Are assertions meaningful?
   - Do tests follow AAA pattern (Arrange, Act, Assert)?
3. Output findings as a prioritized list:

```markdown
## Test Quality Findings

### HIGH Priority
- [file]: [issue description]

### MEDIUM Priority
- [file]: [issue description]

### LOW Priority
- [file]: [issue description]

## Coverage Assessment
- Lines covered: X%
- Critical paths tested: Yes/No
- Edge cases addressed: Yes/No
```

**Rules:**
- Focus on missing tests, not style preferences
- Identify only actionable improvements
- Acknowledge good patterns observed
