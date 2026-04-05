# Story 14.4: Language Switcher Component

Status: done

## Story

As a user,
I want to manually switch between English and Traditional Chinese,
so that I can use the app in my preferred language.

## Epic

Epic 14: Traditional Chinese i18n (Duolanguage Support)

## Dependencies

- Story 14.1 (i18n Infrastructure Setup) MUST be completed first
- Story 14.2 (English Translation Baseline) SHOULD be completed

## Acceptance Criteria

### AC-1: Language Switcher Visible
**Given** the application is loaded
**When** the user looks at the UI
**Then** a language switcher is visible in the sidebar or header
**And** it displays the current language (e.g., "EN" or "繁體中文")

### AC-2: Dropdown Shows Available Languages
**Given** the application is loaded
**When** the user clicks the language switcher
**Then** a dropdown shows available languages: English, 繁體中文

### AC-3: Immediate Re-render
**Given** the user selects a language from dropdown
**When** the selection changes
**Then** all UI text immediately re-renders without page reload
**And** i18n.changeLanguage() is called to update the language

### AC-4: Language Persistence
**Given** the user selects a language
**When** the page is reloaded or reopened
**Then** the selected language is persisted to localStorage
**And** the previously selected language is restored

### AC-5: Current Language Indication
**Given** the dropdown is open
**When** the user views the language options
**Then** the currently selected language is visually indicated (e.g., checkmark or highlight)

## Tasks / Subtasks

- [x] Task 1: Create LanguageSwitcher component (AC: 1, 2, 3, 4, 5)
  - [x] Subtask 1.1: Create `src/components/LanguageSwitcher.tsx`
  - [x] Subtask 1.2: Create dropdown UI with language options
  - [x] Subtask 1.3: Implement i18n.changeLanguage() call on selection
  - [x] Subtask 1.4: Add visual indication of current language
  - [x] Subtask 1.5: Style the dropdown appropriately

- [x] Task 2: Integrate switcher into AppNavigation (AC: 1)
  - [x] Subtask 2.1: Add LanguageSwitcher to AppNavigation sidebar
  - [x] Subtask 2.2: Position appropriately (typically at bottom or top of sidebar)
  - [x] Subtask 2.3: Ensure responsive behavior on mobile

- [x] Task 3: Verify persistence and re-render (AC: 3, 4)
  - [x] Subtask 3.1: Test language persists across page reload
  - [x] Subtask 3.2: Test immediate UI re-render without reload
  - [x] Subtask 3.3: Test localStorage key 'i18nextLng' is set

## Dev Notes

### Component Implementation Pattern
```tsx
import { useTranslation } from 'react-i18next';
import { useState, useRef, useEffect } from 'react';

const languages = [
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'zh-Hant', name: 'Traditional Chinese', nativeName: '繁體中文' }
];

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentLang = languages.find(l => l.code === i18n.language) || languages[0];

  const handleLanguageChange = (langCode: string) => {
    i18n.changeLanguage(langCode);
    setIsOpen(false);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="language-switcher" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="language-switcher__trigger"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span className="language-switcher__current">{currentLang.nativeName}</span>
      </button>

      {isOpen && (
        <ul className="language-switcher__dropdown" role="listbox">
          {languages.map(lang => (
            <li
              key={lang.code}
              role="option"
              aria-selected={lang.code === i18n.language}
              className={`language-switcher__option ${lang.code === i18n.language ? 'active' : ''}`}
              onClick={() => handleLanguageChange(lang.code)}
            >
              {lang.nativeName}
              {lang.code === i18n.language && <span className="check">✓</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

### Styling Requirements
```css
.language-switcher {
  position: relative;
}

.language-switcher__trigger {
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

.language-switcher__dropdown {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  list-style: none;
  padding: 4px 0;
  margin: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 1000;
}

.language-switcher__option {
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.language-switcher__option:hover {
  background: var(--hover-color);
}

.language-switcher__option.active {
  font-weight: 600;
}

.language-switcher__option .check {
  color: var(--primary-color);
}
```

### Source Tree Components to Touch
- `src/components/LanguageSwitcher.tsx` - new component
- `src/components/AppNavigation.tsx` - integrate switcher
- `src/components/AppNavigation.css` or global CSS - styling

### Testing Standards
- Verify dropdown opens on click
- Verify language options show English and 繁體中文
- Verify clicking an option changes the language immediately
- Verify no page reload occurs
- Verify language persists after page reload
- Verify 'i18nextLng' is updated in localStorage
- Verify keyboard accessibility (Tab, Enter, Escape)

## Dev Agent Record

### Completion Notes
- Moved the pill-style `LanguageSwitcher` out of the workspace dropdown and into the visible sidebar footer so the control is available without opening a secondary menu.
- Switched the component to `useTranslation("common")` and `i18n.resolvedLanguage` so the active state, titles, and accessibility labels stay synchronized with the resolved locale.
- Added localized `languageSwitcher.*` strings to both locale bundles for the switcher accessibility copy.

### Validation
- `pnpm build`
- `pnpm lint`
- `pnpm exec vitest run src/pages/settings/SettingsPage.test.tsx src/tests/test_health.test.tsx`

### File List
- `src/components/LanguageSwitcher.tsx`
- `src/components/AppNavigation.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`

### Change Log
- 2026-04-05: Review-fix follow-up — made the language switcher visible in the sidebar footer, localized its accessibility copy, and revalidated frontend build/lint/tests.
