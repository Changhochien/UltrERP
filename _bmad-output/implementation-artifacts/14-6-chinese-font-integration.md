# Story 14.6: Chinese Font Integration

Status: ready-for-dev

## Story

As a system,
I want proper Traditional Chinese font rendering,
so that all Chinese characters display correctly without missing glyph issues.

## Epic

Epic 14: Traditional Chinese i18n (Duolanguage Support)

## Dependencies

- Story 14.3 (Traditional Chinese Translation) SHOULD be completed

## Acceptance Criteria

### AC-1: Font Stack Definition
**Given** the application displays Chinese text
**When** the page renders
**Then** the font stack includes: `"Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif`

### AC-2: Font Loading
**Given** Chinese font is needed
**When** the page loads
**Then** Noto Sans TC is loaded via Google Fonts (or self-hosted for China accessibility)
**And** the font is available before Chinese text renders

### AC-3: Font Display Strategy
**Given** Noto Sans TC is loaded
**When** the font is being applied
**Then** `font-display` is set to `'optional'` for performance
**And** text is visible immediately even if custom font hasn't loaded

### AC-4: No Tofu (Missing Character) Issues
**Given** the application displays Chinese text
**When** all fonts are configured correctly
**Then** Chinese text renders without tofu (missing character box) issues
**And** fallback fonts (PingFang TC, Microsoft JhengHei) cover any missing glyphs

### AC-5: CSS Applied Globally
**Given** font stack is defined
**When** styles are applied
**Then** font stack is applied globally via CSS (e.g., in index.css or App.css)
**And** all text components inherit the font stack

## Tasks / Subtasks

- [ ] Task 1: Add Google Fonts import for Noto Sans TC (AC: 2)
  - [ ] Subtask 1.1: Add Google Fonts link for Noto Sans TC in index.html
  - [ ] Subtask 1.2: Alternatively, configure in CSS @import
  - [ ] Subtask 1.3: Verify font URL is accessible

- [ ] Task 2: Configure font-display: optional (AC: 3)
  - [ ] Subtask 2.1: Configure Google Fonts URL with `&display=optional`
  - [ ] Subtask 2.2: Or use CSS font-face with font-display: optional
  - [ ] Subtask 2.3: Verify fallback fonts work while custom font loads

- [ ] Task 3: Apply font stack globally (AC: 1, 5)
  - [ ] Subtask 3.1: Update global CSS or index.css with font-family stack
  - [ ] Subtask 3.2: Apply to body or root element
  - [ ] Subtask 3.3: Verify all components inherit font stack

- [ ] Task 4: Verify Chinese text rendering (AC: 4)
  - [ ] Subtask 4.1: Test zh-Hant translation displays correctly
  - [ ] Subtask 4.2: Test various Chinese characters render without tofu
  - [ ] Subtask 4.3: Test fallback to PingFang TC on macOS
  - [ ] Subtask 4.4: Test fallback to Microsoft JhengHei on Windows

## Dev Notes

### Google Fonts Integration

In `public/index.html`, add to `<head>`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=optional" rel="stylesheet">
```

Or in CSS (`src/index.css`):
```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=optional');
```

### Alternative: Self-Hosted Font for China

For China accessibility, self-host Noto Sans TC:

1. Download font files from https://fonts.google.com/download?family=Noto%20Sans%20TC
2. Place in `public/fonts/`
3. Use CSS @font-face:

```css
@font-face {
  font-family: 'Noto Sans TC';
  font-style: normal;
  font-weight: 400 700;
  font-display: optional;
  src: url('/fonts/NotoSansTC-Regular.woff2') format('woff2'),
       url('/fonts/NotoSansTC-Regular.woff') format('woff');
}
```

### Global Font Stack CSS

In `src/index.css`:
```css
:root {
  --font-family-base: 'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif;
}

body {
  font-family: var(--font-family-base);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Or apply directly */
body, button, input, select, textarea {
  font-family: 'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif;
}
```

### Font Stack Explanation

| Font | Platform | Notes |
|------|----------|-------|
| Noto Sans TC | Cross-platform | Google's Traditional Chinese font, comprehensive coverage |
| PingFang TC | macOS/iOS | Apple's Traditional Chinese font |
| Microsoft JhengHei | Windows | Microsoft's Traditional Chinese font |

### Font Display: optional

Using `font-display: optional` means:
- Font is downloaded asynchronously
- If font is not ready when text renders, fallback font is used
- Font will be cached for next page load
- No invisible text (unlike `font-display: block`)
- No layout shift (unlike `font-display: swap`)

### Source Tree Components to Touch
- `public/index.html` - add Google Fonts link
- `src/index.css` or `src/App.css` - add font-family stack

### Testing Standards
- Verify Noto Sans TC loads successfully
- Verify Chinese text renders without tofu
- Verify font-display: optional works (fallback fonts used while loading)
- Verify on macOS: PingFang TC renders correctly
- Verify on Windows: Microsoft JhengHei renders correctly
- Verify no FOIT (flash of invisible text)
- Verify no FOUT (flash of unstyled text) significant enough to cause layout issues
