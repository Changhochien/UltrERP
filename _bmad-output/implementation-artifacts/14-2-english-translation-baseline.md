# Story 14.2: English Translation Baseline

Status: ready-for-dev

## Story

As a system,
I want all current UI strings extracted to English translation files,
so that we have a complete English baseline to translate from.

## Epic

Epic 14: Traditional Chinese i18n (Duolanguage Support)

## Dependencies

- Story 14.1 (i18n Infrastructure Setup) MUST be completed first

## Acceptance Criteria

### AC-1: English Translation File Exists
**Given** i18next is configured
**When** the application renders UI components
**Then** English translation file exists at `/public/locales/en/common.json`

### AC-2: Common Namespace Coverage
**Given** English translation file exists
**When** translations are loaded
**Then** common.json contains keys for: nav, buttons, labels, messages, errors, validation

### AC-3: All Components Use Translation Hook
**Given** i18next is configured
**When** React components render visible text
**Then** all React components use the `useTranslation` hook or `t()` function
**And** no hardcoded English strings remain in component render methods

### AC-4: Translation Key Structure
**Given** common.json exists
**When** keys are organized
**Then** keys follow hierarchical naming: `{category}.{subcategory}.{key}`
**And** Example structure:
```json
{
  "nav": {
    "dashboard": "Dashboard",
    "customers": "Customers",
    "invoices": "Invoices",
    "inventory": "Inventory"
  },
  "buttons": {
    "save": "Save",
    "cancel": "Cancel",
    "delete": "Delete",
    "edit": "Edit",
    "add": "Add"
  },
  "labels": {
    "name": "Name",
    "email": "Email",
    "phone": "Phone",
    "address": "Address"
  },
  "messages": {
    "loading": "Loading...",
    "success": "Operation completed successfully",
    "noData": "No data available"
  },
  "errors": {
    "required": "This field is required",
    "invalidEmail": "Please enter a valid email address",
    "networkError": "Network error. Please try again."
  },
  "validation": {
    "minLength": "Must be at least {count} characters",
    "maxLength": "Must be no more than {count} characters"
  }
}
```

## Tasks / Subtasks

- [ ] Task 1: Audit existing UI strings across all components (AC: 3)
  - [ ] Subtask 1.1: Run codebase grep for hardcoded strings in JSX
  - [ ] Subtask 1.2: List all components with visible text
  - [ ] Subtask 1.3: Categorize strings by type (nav, buttons, labels, messages, errors, validation)

- [ ] Task 2: Create comprehensive English translation file (AC: 1, 2, 4)
  - [ ] Subtask 2.1: Create `/public/locales/en/common.json`
  - [ ] Subtask 2.2: Add all navigation strings under `nav` key
  - [ ] Subtask 2.3: Add all button strings under `buttons` key
  - [ ] Subtask 2.4: Add all label strings under `labels` key
  - [ ] Subtask 2.5: Add all message strings under `messages` key
  - [ ] Subtask 2.6: Add all error strings under `errors` key
  - [ ] Subtask 2.7: Add all validation strings under `validation` key
  - [ ] Subtask 2.8: Include interpolation placeholders where needed (e.g., {count}, {field})

- [ ] Task 3: Refactor components to use useTranslation hook (AC: 3)
  - [ ] Subtask 3.1: Refactor AppNavigation component
  - [ ] Subtask 3.2: Refactor all page components (Dashboard, Customers, Invoices, Inventory)
  - [ ] Subtask 3.3: Refactor form components (CustomerForm, InvoiceLineEditor)
  - [ ] Subtask 3.4: Refactor dialog components (CustomerDetailDialog)
  - [ ] Subtask 3.5: Refactor card components (RevenueCard, TopProductsCard, etc.)
  - [ ] Subtask 3.6: Replace all hardcoded strings with t('key.path') calls

- [ ] Task 4: Verify no hardcoded strings remain (AC: 3)
  - [ ] Subtask 4.1: Grep for non-translated visible text patterns
  - [ ] Subtask 4.2: Verify all visible strings use t() function
  - [ ] Subtask 4.3: Test all UI flows to ensure translations appear

## Dev Notes

### Translation Hook Usage Pattern
```tsx
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation('common');

  return (
    <div>
      <h1>{t('nav.dashboard')}</h1>
      <button>{t('buttons.save')}</button>
      <span>{t('messages.loading')}</span>
    </div>
  );
}
```

### Key Interpolation Examples
```json
{
  "validation": {
    "minLength": "Must be at least {count} characters",
    "greeting": "Hello, {name}!"
  }
}
```

### Source Tree Components to Touch
- `public/locales/en/common.json` - new file with all English translations
- `src/components/AppNavigation.tsx`
- `src/components/customers/CustomerForm.tsx`
- `src/components/customers/CustomerDetailDialog.tsx`
- `src/components/invoices/InvoiceLineEditor.tsx`
- `src/domain/dashboard/components/*.tsx` (all dashboard card components)
- Any other components with visible text

### Testing Standards
- Verify all components use t() for visible text
- Verify no console warnings for missing translation keys
- Verify interpolation works correctly with dynamic values
- Verify plural forms are correctly structured (English has singular/plural)

### Important Notes
- English baseline MUST be comprehensive - all visible strings
- This is the source of truth for translation keys
- Chinese translation will mirror this structure
- Maintain consistency in key naming across files
