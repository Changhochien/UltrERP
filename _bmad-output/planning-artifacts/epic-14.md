## Epic 14: Traditional Chinese i18n (Duolanguage Support)

### Epic Goal

System displays all UI text in both English and Traditional Chinese (zh-Hant), with automatic browser language detection and manual language switching, providing a truly bilingual ERP experience for Taiwan SMB users.

### Story 14.1: i18n Infrastructure Setup

As a system,
I want to integrate react-i18next with locale detection and lazy-loaded translation files,
So that the application is ready for multilingual support.

**Acceptance Criteria:**

**Given** the React application is bootstrapped
**When** the user first loads the application
**Then** i18next is configured with react-i18next, i18next-browser-languagedetector, and i18next-http-backend
**And** supported languages are ['en', 'zh-Hant']
**And** fallback language is 'en'
**And** translation files are lazy-loaded from /locales/{lng}/{ns}.json
**And** detection order is: localStorage → navigator.language → querystring
**And** language preference is cached in localStorage under key 'i18nextLng'

### Story 14.2: English Translation Baseline

As a system,
I want all current UI strings extracted to English translation files,
So that we have a complete English baseline to translate from.

**Acceptance Criteria:**

**Given** i18next is configured
**When** the application renders UI components
**Then** all visible text strings are sourced from translation keys
**And** English translation files exist at /public/locales/en/common.json
**And** common.json contains keys for: nav, buttons, labels, messages, errors, validation
**And** all existing React components use the useTranslation hook or t() function
**And** no hardcoded English strings remain in component render methods

### Story 14.3: Traditional Chinese Translation

As a system,
I want complete Traditional Chinese (zh-Hant) translation files,
So that Taiwanese users see all text in their native language.

**Acceptance Criteria:**

**Given** English baseline exists
**When** user selects zh-Hant language
**Then** all UI text displays in Traditional Chinese
**And** translation files exist at /public/locales/zh-Hant/common.json
**And** Chinese plural handling uses only 'other' category (no singular/plural distinction)
**And** all vocabulary uses Taiwanese variants (例如: 電腦 rather than 計算機 for computer)
**And** character conversion (OpenCC-style) is NOT used for UI translation

### Story 14.4: Language Switcher Component

As a user,
I want to manually switch between English and Traditional Chinese,
So that I can use the app in my preferred language.

**Acceptance Criteria:**

**Given** the application is loaded
**When** the user clicks the language switcher
**Then** a dropdown shows available languages: English, 繁體中文
**And** selecting a language immediately re-renders all UI text without page reload
**And** selected language is persisted to localStorage
**And** the switcher displays the current language name/flag
**And** the switcher is accessible from the sidebar or header

### Story 14.5: Browser Language Auto-Detection

As a system,
I want to automatically detect and apply the user's browser language preference,
So that users see the correct language on first visit without manual selection.

**Acceptance Criteria:**

**Given** it's the user's first visit
**When** the application loads
**Then** navigator.language is read (e.g., "zh-TW", "zh-Hant", "zh-CN")
**And** the system maps it to supported locale (zh-TW/zh-Hant → zh-Hant, others → en)
**And** detected language is applied before first render
**And** if navigator.language starts with 'zh', zh-Hant is selected by default

### Story 14.6: Chinese Font Integration

As a system,
I want proper Traditional Chinese font rendering,
So that all Chinese characters display correctly without missing glyph issues.

**Acceptance Criteria:**

**Given** the application displays Chinese text
**When** the page renders
**Then** the font stack includes: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif
**And** Noto Sans TC is loaded via Google Fonts (or self-hosted for China accessibility)
**And** font-display is set to 'optional' for performance
**And** Chinese text renders without tofu (missing character) issues

---

