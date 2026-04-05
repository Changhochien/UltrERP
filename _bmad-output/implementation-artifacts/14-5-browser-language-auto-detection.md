# Story 14.5: Browser Language Auto-Detection

Status: done

## Story

As a system,
I want to automatically detect and apply the user's browser language preference,
so that users see the correct language on first visit without manual selection.

## Epic

Epic 14: Traditional Chinese i18n (Duolanguage Support)

## Dependencies

- Story 14.1 (i18n Infrastructure Setup) MUST be completed first

## Acceptance Criteria

### AC-1: Browser Language Detection
**Given** it's the user's first visit
**When** the application loads
**Then** navigator.language is read (e.g., "zh-TW", "zh-Hant", "zh-CN", "en-US")

### AC-2: Language Mapping
**Given** navigator.language is read
**When** the language is determined
**Then** the system maps it to supported locale:
- "zh-TW" / "zh-Hant" / "zh-HK" → "zh-Hant"
- "zh-CN" / "zh-SG" / "zh-MO" → NOT mapped to zh-Hant (falls back to 'en')
- "en-US" / "en-GB" / "en-AU" → "en"
- Other → "en" (fallback)

### AC-3: Pre-First-Render Application
**Given** browser language is detected
**When** the application renders
**Then** detected language is applied before first render
**And** user sees correct language immediately (no flash of wrong language)

### AC-4: zh-Hant Default for Chinese Browsers
**Given** navigator.language starts with 'zh'
**When** the language is evaluated
**Then** zh-Hant is selected if the browser locale is Traditional Chinese variant
**And** specifically: "zh-TW", "zh-Hant" → "zh-Hant"

## Tasks / Subtasks

- [x] Task 1: Configure i18next browser language detection (AC: 1, 2, 3, 4)
  - [x] Subtask 1.1: Configure i18next-browser-languagedetector in src/i18n.ts
  - [x] Subtask 1.2: Configure custom language mapping for zh-TW/zh-Hant → zh-Hant
  - [x] Subtask 1.3: Ensure detection happens before first render (not after)
  - [x] Subtask 1.4: Configure order: localStorage → navigator.language → querystring

- [x] Task 2: Implement custom language mapping (AC: 2, 4)
  - [x] Subtask 2.1: Create custom lookup function for Chinese variants
  - [x] Subtask 2.2: Map "zh-TW" → "zh-Hant"
  - [x] Subtask 2.3: Map "zh-Hant" → "zh-Hant"
  - [x] Subtask 2.4: Map "zh-HK" → "zh-Hant"
  - [x] Subtask 2.5: Ensure "zh-CN" does NOT map to zh-Hant (falls back to 'en')

- [x] Task 3: Test pre-first-render detection (AC: 3)
  - [x] Subtask 3.1: Verify language is applied before React renders
  - [x] Subtask 3.2: Verify no flash of untranslated content
  - [x] Subtask 3.3: Test with various browser locales (zh-TW, zh-CN, en-US)

## Dev Notes

### i18next Configuration for Browser Detection

```typescript
// src/i18n.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import HttpBackend from 'i18next-http-backend';

const LANGUAGE_MAPPING: Record<string, string> = {
  'zh-TW': 'zh-Hant',
  'zh-Hant': 'zh-Hant',
  'zh-HK': 'zh-Hant',
  // Note: zh-CN does NOT map to zh-Hant - falls back to 'en'
};

i18n
  .use(HttpBackend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    supportedLngs: ['en', 'zh-Hant'],
    ns: ['common'],
    defaultNS: 'common',

    detection: {
      // Detection order
      order: ['localStorage', 'navigatorLanguage', 'querystring'],

      // Keys to check
      lookupLocalStorage: 'i18nextLng',
      lookupQuerystring: 'lng',

      // Custom navigator language detection
      caches: ['localStorage'],

      // Language conversion
      convertDetectedLanguage: (lng: string) => {
        // Map browser language to supported language
        return LANGUAGE_MAPPING[lng] || lng;
      },
    },

    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },

    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
```

### Alternative: Custom Detector Function

If i18next-browser-languagedetector doesn't support custom mapping directly:

```typescript
// Custom language detector
const customLanguageDetector = {
  name: 'customLanguageDetector',

  lookup() {
    // Check localStorage first
    const stored = localStorage.getItem('i18nextLng');
    if (stored && ['en', 'zh-Hant'].includes(stored)) {
      return stored;
    }

    // Check navigator.language
    const browserLng = navigator.language;
    const mappedLng = LANGUAGE_MAPPING[browserLng];

    if (mappedLng) {
      return mappedLng;
    }

    // Check if navigator.language starts with 'en'
    if (browserLng.startsWith('en')) {
      return 'en';
    }

    // Default to 'en'
    return 'en';
  },

  cacheUserLanguage(lng: string) {
    localStorage.setItem('i18nextLng', lng);
  }
};

// Use custom detector
i18n.use(customLanguageDetector);
```

### Critical: Pre-First-Render Detection

The language detection MUST happen before React renders to avoid:
1. Flash of untranslated content (FOTC)
2. Language flicker on initial load

This requires:
- i18n initialization in `main.tsx` or `index.tsx` BEFORE `ReactDOM.render()`
- Language detector running synchronously on init

```typescript
// src/main.tsx (or index.tsx)
import i18n from './i18n'; // Initialize i18n BEFORE React renders

const root = ReactDOM.createRoot(document.getElementById('root')!);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### Source Tree Components to Touch
- `src/i18n.ts` - update detection configuration
- `src/main.tsx` or `src/index.tsx` - ensure i18n loads before React

### Testing Standards
- Test with browser locale set to "zh-TW" → should show zh-Hant
- Test with browser locale set to "zh-CN" → should fall back to 'en'
- Test with browser locale set to "en-US" → should show 'en'
- Test with localStorage set to 'zh-Hant' → should override browser detection
- Test with querystring `?lng=zh-Hant` → should override all
- Verify no language flicker on first load

## Dev Agent Record

### Completion Notes
- Added explicit `mapDetectedLanguage()` normalization in `src/i18n.ts` so Traditional Chinese browser locales (`zh-TW`, `zh-Hant`, `zh-HK`) resolve to `zh-Hant`, English variants normalize to `en`, and unsupported Chinese variants fall back to English.
- Kept initialization in the App import chain before first render and synchronized `document.documentElement.lang` to the resolved locale after init and on language changes.
- Preserved the existing detector priority of localStorage → navigator → querystring while ensuring normalized values are what get cached.

### Validation
- `pnpm build`
- `pnpm lint`
- Locale parity recount: `270` English keys / `270` zh-Hant keys, with no missing keys on either side.

### File List
- `src/i18n.ts`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`

### Change Log
- 2026-04-05: Review-fix follow-up — implemented explicit detected-language normalization, synced the document language, and revalidated locale parity plus frontend build/lint.
