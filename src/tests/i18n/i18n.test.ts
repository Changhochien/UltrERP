/**
 * i18n Translation Tests
 * 
 * Validates that:
 * 1. All translation keys exist in all supported locales
 * 2. Placeholder counts match between locales
 * 3. No empty or malformed translations
 */

import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

const LOCALES_DIR = path.join(process.cwd(), 'public', 'locales');
const LOCALES = ['en', 'zh-Hant'] as const;
const NAMESPACES = [
  'common', 'shell', 'routes', 'auth', 'dashboard', 'admin',
  'intelligence', 'crm', 'customer', 'inventory', 'orders',
  'procurement', 'purchase', 'invoice', 'payments', 'settings'
] as const;

type Locale = typeof LOCALES[number];
type Namespace = typeof NAMESPACES[number];

interface TranslationEntry {
  key: string;
  value: unknown;
  path: string;
}

function flattenObject(obj: unknown, prefix = ''): TranslationEntry[] {
  const entries: TranslationEntry[] = [];
  
  if (typeof obj !== 'object' || obj === null) return entries;
  
  for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
    const fullPath = prefix ? `${prefix}.${key}` : key;
    
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      entries.push(...flattenObject(value, fullPath));
    } else {
      entries.push({ key: fullPath, value, path: fullPath });
    }
  }
  
  return entries;
}

function extractPlaceholders(value: string): string[] {
  // Match {{variable}} or {variable}
  const matches = value.match(/\{\{[^}]+\}\}|\{[^}]+\}/g) || [];
  return matches;
}

function loadTranslations(locale: Locale, namespace: Namespace): Record<string, unknown> {
  const filePath = path.join(LOCALES_DIR, locale, `${namespace}.json`);
  
  if (!fs.existsSync(filePath)) {
    return {};
  }
  
  const content = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(content);
}

describe('i18n Translation Integrity', () => {
  describe.each(NAMESPACES)('Namespace: %s', (namespace) => {
    const enTranslations = loadTranslations('en', namespace);
    const zhTranslations = loadTranslations('zh-Hant', namespace);
    
    const enEntries = flattenObject(enTranslations);
    const zhEntries = flattenObject(zhTranslations);
    
    const enKeys = new Set(enEntries.map(e => e.key));
    const zhKeys = new Set(zhEntries.map(e => e.key));
    
    // Keys in en but missing in zh-Hant
    const missingInZh = [...enKeys].filter(k => !zhKeys.has(k));
    
    // Keys in zh-Hant but not in en (extra)
    const extraInZh = [...zhKeys].filter(k => !enKeys.has(k));
    
    it('should have no missing translations in zh-Hant', () => {
      expect(missingInZh, `Missing keys: ${missingInZh.join(', ')}`).toHaveLength(0);
    });
    
    it('should have no extra translations in zh-Hant', () => {
      expect(extraInZh, `Extra keys: ${extraInZh.join(', ')}`).toHaveLength(0);
    });
    
    it('should have matching placeholder counts for translated strings', () => {
      const mismatches: string[] = [];
      
      for (const entry of enEntries) {
        if (typeof entry.value !== 'string') continue;
        
        const zhEntry = zhEntries.find(e => e.key === entry.key);
        if (!zhEntry || typeof zhEntry.value !== 'string') continue;
        
        const enPlaceholders = extractPlaceholders(entry.value);
        const zhPlaceholders = extractPlaceholders(zhEntry.value);
        
        if (enPlaceholders.length !== zhPlaceholders.length) {
          mismatches.push(
            `${entry.key}: en=${enPlaceholders.length}, zh-Hant=${zhPlaceholders.length}`
          );
        }
      }
      
      expect(mismatches, `Placeholder mismatches:\n${mismatches.join('\n')}`).toHaveLength(0);
    });
  });
  
  describe('No empty translations', () => {
    it.each(LOCALES)('Locale %s should have no empty string values', (locale) => {
      const emptyKeys: string[] = [];
      
      for (const namespace of NAMESPACES) {
        const translations = loadTranslations(locale, namespace);
        const entries = flattenObject(translations);
        
        for (const entry of entries) {
          if (entry.value === '' || entry.value === null) {
            emptyKeys.push(`${namespace}:${entry.key}`);
          }
        }
      }
      
      expect(emptyKeys, `Empty translations:\n${emptyKeys.join('\n')}`).toHaveLength(0);
    });
  });
  
  describe('JSON validity', () => {
    it.each(NAMESPACES)('Namespace %s should have valid JSON in all locales', (namespace) => {
      for (const locale of LOCALES) {
        const filePath = path.join(LOCALES_DIR, locale, `${namespace}.json`);
        const content = fs.readFileSync(filePath, 'utf-8');
        
        expect(() => JSON.parse(content), `${locale}/${namespace} should be valid JSON`).not.toThrow();
      }
    });
  });
});
