# Story 14.3: Traditional Chinese Translation

Status: ready-for-dev

## Story

As a system,
I want complete Traditional Chinese (zh-Hant) translation files,
so that Taiwanese users see all text in their native language.

## Epic

Epic 14: Traditional Chinese i18n (Duolanguage Support)

## Dependencies

- Story 14.2 (English Translation Baseline) MUST be completed first

## Acceptance Criteria

### AC-1: Chinese Translation File Exists
**Given** English baseline exists
**When** user selects zh-Hant language
**Then** translation file exists at `/public/locales/zh-Hant/common.json`

### AC-2: All English Keys Translated
**Given** English baseline exists
**When** zh-Hant translations are created
**Then** all keys from en/common.json exist in zh-Hant/common.json
**And** all values are translated to Traditional Chinese

### AC-3: Chinese Plural Handling
**Given** translations are configured
**When** plural forms are used
**Then** Chinese plural handling uses only 'other' category
**And** no singular/plural distinction is made
**And** Example: `{"other": "項目"}` instead of `{"one": "項目", "other": "項目"}`

### AC-4: Taiwanese Vocabulary
**Given** zh-Hant translations exist
**When** translations are created
**Then** all vocabulary uses Taiwanese variants
**And** Example mappings:
- 電腦 (not 計算機) for computer
- 軟體 (not 软件) for software
- 網站 (not 网站) for website
- 資料 (not 数据) for data
- 資訊 (not 信息) for information
- 訊息 (not 消息) for message
- 記憶體 (not 内存) for memory
- 周邊設備 (not 外设) for peripheral
- 印表機 (not 打印机) for printer
- 鍵盤 (not 键盘) for keyboard
- 滑鼠 (not 鼠标) for mouse

### AC-5: No Character Conversion
**Given** zh-Hant translations exist
**When** translations are created
**Then** OpenCC-style character conversion is NOT used
**And** all text is natively written in Traditional Chinese
**And** translations are human-written, not machine-converted

## Tasks / Subtasks

- [ ] Task 1: Create Traditional Chinese translation file (AC: 1, 2, 3, 4, 5)
  - [ ] Subtask 1.1: Copy structure from en/common.json
  - [ ] Subtask 1.2: Translate all navigation strings to zh-Hant
  - [ ] Subtask 1.3: Translate all button strings to zh-Hant
  - [ ] Subtask 1.4: Translate all label strings to zh-Hant
  - [ ] Subtask 1.5: Translate all message strings to zh-Hant
  - [ ] Subtask 1.6: Translate all error strings to zh-Hant
  - [ ] Subtask 1.7: Translate all validation strings to zh-Hant
  - [ ] Subtask 1.8: Apply Taiwanese vocabulary standards

- [ ] Task 2: Configure Chinese plural handling (AC: 3)
  - [ ] Subtask 2.1: Configure i18next to use 'other' only for Chinese
  - [ ] Subtask 2.2: Remove singular form from zh-Hant translations
  - [ ] Subtask 2.3: Verify pluralization works with 'other' category only

- [ ] Task 3: Verify translation quality (AC: 4, 5)
  - [ ] Subtask 3.1: Review all translations for Taiwanese vocabulary
  - [ ] Subtask 3.2: Verify no Simplified Chinese characters
  - [ ] Subtask 3.3: Verify natural Traditional Chinese phrasing

## Dev Notes

### Taiwanese Vocabulary Reference

| English | Taiwanese (zh-Hant) | Avoid (zh-CN) |
|---------|---------------------|---------------|
| computer | 電腦 | 計算機/电脑 |
| software | 軟體 | 软件 |
| website | 網站 | 网站 |
| data | 資料 | 数据 |
| information | 資訊 | 信息 |
| message | 訊息 | 消息 |
| memory | 記憶體 | 内存 |
| keyboard | 鍵盤 | 键盘 |
| mouse | 滑鼠 | 鼠标 |
| printer | 印表機 | 打印机 |
| peripheral | 周邊設備 | 外设 |

### zh-Hant Translation Structure Example
```json
{
  "nav": {
    "dashboard": "控制台",
    "customers": "客戶",
    "invoices": "發票",
    "inventory": "庫存"
  },
  "buttons": {
    "save": "儲存",
    "cancel": "取消",
    "delete": "刪除",
    "edit": "編輯",
    "add": "新增"
  },
  "labels": {
    "name": "名稱",
    "email": "電子郵件",
    "phone": "電話",
    "address": "地址"
  },
  "messages": {
    "loading": "載入中...",
    "success": "操作成功",
    "noData": "目前沒有資料"
  },
  "errors": {
    "required": "此欄位為必填",
    "invalidEmail": "請輸入有效的電子郵件地址",
    "networkError": "網路錯誤，請稍後再試"
  },
  "validation": {
    "minLength": "至少需要 {count} 個字元",
    "maxLength": "不能超過 {count} 個字元"
  }
}
```

### Chinese Plural Configuration
In `src/i18n.ts`, configure Chinese to use 'other' only:
```typescript
resources: {
  en: { common: {} },
  'zh-Hant': {
    common: {},
    translation: {
      // Chinese uses 'other' for all counts
    }
  }
}

// In i18next config:
pluralSeparator: '_',
contextSeparator: '_',
```

### File Structure
```
public/locales/
  en/
    common.json       # English baseline
  zh-Hant/
    common.json       # Traditional Chinese translations
```

### Testing Standards
- Verify all keys from en/common.json exist in zh-Hant/common.json
- Verify all translations are in Traditional Chinese (not Simplified)
- Verify Taiwanese vocabulary is used consistently
- Verify Chinese plural handling works with 'other' only
- Verify interpolation placeholders ({count}, {name}) are preserved
