# i18n Architecture Guide

This document describes the internationalization (i18n) architecture for UltrERP and how to maintain translation quality.

## 📁 Directory Structure

```
public/locales/
├── en/                    # English (Source of Truth)
│   ├── common.json
│   ├── shell.json
│   ├── routes.json
│   ├── orders.json
│   └── ...
└── zh-Hant/               # Traditional Chinese
    ├── common.json
    ├── shell.json
    └── ...

src/lib/i18n/
├── types.ts               # Type definitions
├── namespaces.ts           # Namespace constants
├── generated-keys.ts      # Auto-generated key types
└── locale-manifest.json    # Translation manifest

scripts/
├── i18n-validate.ts       # Full validation
├── i18n-check.ts          # Pre-commit check
├── i18n-coverage.ts       # Coverage report
├── generate-i18n-types.ts # Type generation
└── i18n-pre-commit.sh     # Pre-commit hook

src/tests/i18n/
└── i18n.test.ts          # Translation tests
```

## 🔑 Key Concepts

### 1. Source of Truth
- **English (`en`)** is the source of truth for all translation keys
- All other locales must have the same keys
- When adding new features, add translations to English first

### 2. Translation Keys
- Use dot notation: `section.subsection.key`
- Example: `orders.form.customerPlaceholder`
- Avoid camelCase in keys; use snake_case: `customer_id` not `customerId`

### 3. Placeholders
- Format: `{{variableName}}` or `{variableName}`
- Must match between all locales
- Example: `"Hello {{name}}, you have {{count}} items"`

## 🛠️ Tools

### Validation Script
```bash
npx tsx scripts/i18n-validate.ts
```
Checks for:
- Missing translations
- Malformed JSON
- Placeholder count mismatches
- Empty values

### Pre-commit Check
```bash
node scripts/i18n-check.ts
```
Blocks commits with translation errors.

### Coverage Report
```bash
npx tsx scripts/i18n-coverage.ts
```
Generates a coverage report for all locales.

### Type Generation
```bash
npx tsx scripts/generate-i18n-types.ts
```
Generates TypeScript types from locale JSON files.

## 📋 Adding New Translations

### Step 1: Add to English Locale
```json
// public/locales/en/orders.json
{
  "form": {
    "newField": "New field label"
  }
}
```

### Step 2: Add to All Other Locales
```json
// public/locales/zh-Hant/orders.json
{
  "form": {
    "newField": "新欄位標籤"
  }
}
```

### Step 3: Verify
```bash
npx tsx scripts/i18n-validate.ts
```

## 🧪 Testing

### Run Translation Tests
```bash
pnpm test src/tests/i18n/i18n.test.ts
```

### Add New Tests
```typescript
// src/tests/i18n/i18n.test.ts
it('should have correct placeholder count', () => {
  const en = loadTranslations('en', 'orders');
  const zh = loadTranslations('zh-Hant', 'orders');
  
  expect(getPlaceholderCount(en)).toBe(getPlaceholderCount(zh));
});
```

## 🔌 Integration

### CI/CD (GitHub Actions)
The `i18n.yml` workflow runs on every PR that changes locale files:
- Validates translation parity
- Generates type definitions
- Posts coverage reports

### Pre-commit Hook
Install the hook:
```bash
cp scripts/i18n-pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Or use Husky:
```bash
npx husky add .husky/pre-commit "npx tsx scripts/i18n-check.ts"
```

## 📊 Coverage Requirements

| Metric | Minimum | Target |
|--------|---------|--------|
| Key Parity | 100% | 100% |
| zh-Hant Coverage | 95% | 99% |
| Placeholder Match | 100% | 100% |

## ❌ Common Issues

### 1. Missing Translation
```bash
❌ Missing translation: "orders.form.newField"
```
**Fix**: Add the key to the missing locale.

### 2. Placeholder Mismatch
```bash
⚠️ Placeholder mismatch: en=2, zh-Hant=1
```
**Fix**: Ensure both locales have the same number of placeholders.

### 3. Empty Value
```bash
⚠️ Empty translation value
```
**Fix**: Add a translation value or mark as optional.

## 📖 Best Practices

1. **Never remove translation keys** - Deprecate them with a comment
2. **Always add translations in pairs** - English + target locale
3. **Use descriptive keys** - `error.customerNotFound` not `err.cnt`
4. **Group related keys** - Use nested objects: `form.*`, `error.*`, `label.*`
5. **Keep translations concise** - UI space is limited
6. **Test in both languages** - Don't assume translation fits

## 🔧 Configuration

### Adding a New Locale
1. Create directory: `public/locales/<locale>/`
2. Copy all namespace files from English
3. Translate all values
4. Update `I18N_NAMESPACES` in `src/lib/i18n-namespaces.ts`
5. Run: `npx tsx scripts/generate-i18n-types.ts`

### Adding a New Namespace
1. Create file: `public/locales/en/<namespace>.json`
2. Add to `NAMESPACES` array in scripts
3. Update types and tests
4. Run: `npx tsx scripts/generate-i18n-types.ts`

## 📝 Checklist Before Merging PR

- [ ] All new keys added to English
- [ ] All new keys added to zh-Hant
- [ ] Placeholder counts match
- [ ] No empty translations
- [ ] Validation script passes
- [ ] Tests pass
- [ ] Coverage report shows 95%+
