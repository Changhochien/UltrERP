# UBN Validation (統一編號 Checksum)

## Algorithm
Taiwan Unified Business Numbers are 8-digit identifiers validated with a weighted checksum.

### Steps
1. **Normalize:** Strip all non-digit characters (`re.compile(r"\D")`)
2. **Length check:** Must be exactly 8 digits
3. **Weighted sum:** Multiply each digit by its weight, then sum the digit-sums of each product
   - Weights: `(1, 2, 1, 2, 1, 2, 4, 1)`
   - For each product, sum its individual digits (e.g., `12 → 1 + 2 = 3`)
4. **Validation:** `total % 5 == 0` → valid

### Special Case (7th digit = 7)
When `digits[6] == 7`, accept if **either**:
- `total % 5 == 0`, OR
- `(total + 1) % 5 == 0`

This handles the ambiguity in the weighted product for digit 7 × weight 4 = 28, where digit-sum could be 10 or 11 depending on interpretation.

## Post-2023 Revision
The algorithm was updated from **mod-10** to **mod-5** after 2023 regulatory changes. The codebase implements the current mod-5 rule.

## Examples
| UBN        | Valid | Notes                    |
|------------|-------|--------------------------|
| 04595257   | ✅    | Standard case            |
| 12345675   | ✅    | Digit-7 special case     |
| 00000000   | ❌    | Invalid (all zeros)      |
| 1234       | ❌    | Wrong length             |

## Codebase Reference
- `backend/domains/customers/validators.py` → `validate_taiwan_business_number(raw: str) -> ValidationResult`
- Returns `ValidationResult(valid=bool, error=str|None)`
