# Story 3.2 Validation Report

**Story:** Validate Taiwan Business Number Checksum
**Iteration:** Final (2 iterations completed)
**Validator:** Claude Code
**Date:** 2026-04-01

---

## Status Summary

| Dimension | Status | Severity |
|-----------|--------|----------|
| Completeness | PARTIAL | Medium |
| Consistency | INCONSISTENT | High |
| Correctness | VERIFIED WITH GAPS | High |
| Feasibility | FEASIBLE | Low |
| Best Practices | GOOD | Low |
| Gaps | YES | Medium |

**Overall: READY FOR DEV with fixes required**

---

## Iteration 1 Findings

### Algorithm Verification (via Web Search)

**Critical discovery:** The story correctly warns about "real drift between internal repo wording and current official checksum guidance." Web research confirms:

1. **Official Taiwan UBN Algorithm (from FIA/財政部):**
   - 8 digits (no separate check digit character)
   - Weights: `1, 2, 1, 2, 1, 2, 4, 1` (applied to digits 1-8)
   - Each product is split into individual digits (e.g., 18 → 1 + 8)
   - **OLD numbers (pre-2023):** Sum % 10 == 0
   - **NEW numbers (post-2023):** Sum % 5 == 0
   - **Special case:** If 7th digit is 7, ALSO check (Sum+1) % 5 == 0

2. **PoC validator (`mig41_generator.py`) uses WRONG algorithm:**
   - Uses 9 digits (8 + 1 check digit)
   - Weights: [1, 2] × 4 (alternating)
   - Computes check digit via `(10 - (weighted % 10)) % 10`
   - This is a DIFFERENT algorithm than the official one

3. **The "divisibility-by-5 revision" IS real:**
   - Confirmed from FIA official source: "檢查邏輯由可被『10』整除改為可被『5』整除"
   - Official notice URL in story: https://www.ntbna.gov.tw/singlehtml/bbabfd4af20541b7859b4c5a099081f6
   - Effective April 2023 for new allocations

4. **The "seventh-digit special case" IS real:**
   - When 7th digit is 7, weight 4 produces 28, which splits to 10
   - Formula: valid if (Sum % 5 == 0) OR (Sum % 5 == 4 AND 7th digit == 7)
   - Confirmed with example: 19312376 is valid (Sum=38, 38%5=3, but 39%5=0)

### Key Algorithm Example (from official sources)

```
Number: 19312376
Weights: 1, 2, 1, 2, 1, 2, 4, 1
Products: 1, 18, 3, 4, 2, 4, 28, 6
Split digits: 1, 1+8=9, 3, 4, 2, 4, 2+8=10, 6
Sum = 1+9+3+4+2+4+10+6 = 39
7th digit is 7 → also check (39+1)%5 = 0 → VALID
```

---

## Iteration 2 Findings

### Checking Consistency Across Documents

| Document | What it says | Consistent? |
|----------|--------------|-------------|
| PRD (FR17) | "8 digits + MOD11 check digit" | NO - wrong structure |
| PRD (Journey 2, 4) | "MOD11 validation on tax ID" | NO - wrong algorithm name |
| Architecture | "tax_id (MOD11)" | NO - wrong algorithm |
| PoC mig41_generator.py | 9-digit MOD10 with check digit | NO - wrong algorithm |
| whole-picture.md | "BAN MOD11 validation" | NO - wrong |
| Story 3.2 | "weighted checksum family + divisibility-by-5" | YES - correct direction |

**Critical inconsistency:** The PRD, architecture, and PoC all reference "MOD11" or "MOD10" shorthand that does not match the actual official algorithm. Story 3.2 correctly identifies this drift but uses the term "weighted checksum family" without fully specifying the algorithm.

---

## Confirmed Correct Points

1. **Story correctly identifies the problem:** The repo has stale references to MOD11/MOD10 that do not match current official FIA guidance.

2. **Post-2023 divisibility-by-5 rule is real and verified** from official FIA sources.

3. **Seventh-digit special case is real** - when 7th digit equals 7, an alternative check applies.

4. **Dual-runtime (Python + TypeScript) approach is sound** - both runtimes need the same logic.

5. **Shared fixture strategy is correct** - prevents silent rule drift.

6. **Integration points are correctly scoped** - validator belongs in domain layer, not in route handlers.

---

## Issues (with Severity)

### HIGH: Algorithm Description Incomplete in Story

**Problem:** The story says "weighted checksum family defined by current Ministry of Finance guidance" and "special-case handling for the seventh digit" but does not provide:
- The explicit weight sequence (1, 2, 1, 2, 1, 2, 4, 1)
- The digit-splitting step
- The exact validation formula
- Concrete pass/fail examples

**Impact:** A developer implementing from this story alone cannot determine the correct algorithm. They would need to find and read the official FIA document.

**Fix:** Add explicit algorithm description to acceptance criteria or Dev Notes:

```
Algorithm:
1. Weights for digits 1-8: 1, 2, 1, 2, 1, 2, 4, 1
2. Multiply each digit by its weight
3. Split any two-digit products into individual digits (e.g., 18 → 1, 8)
4. Sum all resulting digits
5. For OLD numbers (issued before April 2023): Sum must be divisible by 10
6. For NEW numbers (issued after April 2023): Sum must be divisible by 5
7. Special case: If 7th digit is 7, also check (Sum+1) is divisible by 5

Example valid numbers:
- 04595257: Sum=40, 40%5=0 → VALID (new format)
- 19312376: Sum=39, (39+1)%5=0 because 7th digit=7 → VALID
```

### HIGH: PRD References Wrong Algorithm Name

**Problem:** PRD FR17 says "8 digits + MOD11 check digit" and Journey 2/4 say "MOD11 validation." These are incorrect - the official algorithm is NOT MOD11.

**Impact:** Future stories may still inherit the wrong terminology, causing continued confusion.

**Fix:** Story 3.2 should explicitly note that "MOD11" references in PRD/architecture are incorrect and should be updated in a subsequent cleanup task.

### MEDIUM: No Clear Rule for Distinguishing Old vs New Numbers

**Problem:** AC2 says "including the post-2023 divisibility-by-5 revision for expanded allocations." But the story does not explain how to determine which rule applies to a given number.

**Impact:** Without knowing which numbers follow which rule, validation is ambiguous.

**Fix:** Add guidance: "The rule is determined by the number's issuance date in the government registry, which is not derivable from the number itself. For maximum compatibility, accept a number if it passes EITHER the divisibility-by-10 OR divisibility-by-5 rule (with the seventh-digit special case applying to both)."

### MEDIUM: Acceptance Criteria Wording is Ambiguous

**Problem:** AC1 says "including the special-case handling for the seventh digit" but does not specify what that case is.

**Impact:** Test acceptance becomes subjective.

**Fix:** Expand AC1 to: "including the special-case handling for when the seventh digit equals 7, which requires an alternative divisibility check."

### MEDIUM: No Test Vectors Provided

**Problem:** The story requires tests with "official example values" but provides none.

**Impact:** Developers must search for official examples, which may not be easily found.

**Fix:** Include at least 3 fixture pairs in the story:
- Valid OLD format number
- Valid NEW format number (7th digit = 7)
- Invalid checksum number

---

## Gaps

1. **No explicit algorithm pseudocode** - the Dev Notes should contain the complete algorithm, not just references to external documents.

2. **No distinction between format validation and checksum validation** - the story should clarify that format validation (8 digits) comes before checksum validation.

3. **No handling for B2C numbers** - the story does not mention whether "0000000000" (B2C placeholder) should be accepted as a special case.

4. **The story references a URL** that is not publicly accessible (ntbna.gov.tw singlehtml endpoint requires browser navigation).

5. **"MOD11" terminology confusion** - the story correctly avoids MOD11 but doesn't explicitly disambiguate from the PRD's use of MOD11.

---

## Recommendations

### Must Fix Before Dev:

1. **Add explicit algorithm specification** to Dev Notes or as an appendix to the story:
   - Weight sequence: 1, 2, 1, 2, 1, 2, 4, 1
   - Digit-splitting step
   - Dual-rule validation (div-by-10 for old, div-by-5 for new)
   - Seventh-digit special case formula

2. **Add concrete test fixtures** to the story:
   - Valid old-format example
   - Valid new-format example with 7th digit = 7
   - Invalid checksum example
   - Format error example (non-8-digits)

3. **Add a note about MOD11 inaccuracy** - explicitly state that PRD references to MOD11 are incorrect and this story implements the actual official algorithm.

### Should Fix:

4. **Clarify acceptance logic** for the dual-rule approach: accept if EITHER rule passes (to handle both old and new numbers in the dataset).

5. **Add uniqueness handling note** for "0000000000" B2C placeholder if applicable.

---

## Validation Checklist

| Check | Result | Notes |
|-------|--------|-------|
| Algorithm matches official FIA guidance | VERIFIED | Div-by-5 and 7th digit special case confirmed |
| Algorithm described explicitly | FAIL | Weight sequence missing from story |
| Dual-runtime approach sound | PASS | Python + TypeScript mirroring is correct |
| Fixture sharing strategy | PASS | Both runtimes should share fixtures |
| Consistency with PRD | FAIL | PRD says MOD11, story avoids it (correct) |
| Consistency with Architecture | FAIL | Architecture says MOD11, story corrects it |
| Consistency with PoC | FAIL | PoC uses wrong algorithm, story knows this |
| Special case for 7th digit | VERIFIED | Real, but not described in story |
| Divisibility-by-5 for new allocations | VERIFIED | Real and documented by FIA |
| Test vectors provided | FAIL | No fixtures in story |
| Integration points clear | PASS | Service layer, not route handlers |

---

## Final Assessment

**Story 3.2 is structurally sound and correctly identifies the problem** - the repo has stale algorithm references that don't match current official FIA guidance. The story's direction to implement "current Ministry of Finance checksum logic" with "post-2023 divisibility-by-5 revision" and "special-case handling for the seventh digit" is correct.

**However, the story lacks the explicit algorithm specification** needed for unambiguous implementation. A developer reading only this story would not know:
- The weights are 1,2,1,2,1,2,4,1
- Two-digit products must be split into single digits before summing
- The valid number is determined by (Sum % 5 == 0) OR (Sum % 5 == 4 AND digit[6] == 7)

**Action required:** Add explicit algorithm pseudocode and at least 3 test fixtures to the story before dev begins. The story otherwise correctly scopes the work and identifies the key risks around stale repo wording vs. official guidance.
