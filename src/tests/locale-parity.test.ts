/**
 * Locale Parity Test Suite
 * 
 * Validates i18n namespace parity between locales:
 * 1. All required namespaces exist in both 'en' and 'zh-Hant'
 * 2. Namespace inventories match between locales
 */

import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

// All required namespaces
const REQUIRED_NAMESPACES = [
  'common',
  'shell',
  'routes',
  'auth',
  'dashboard',
  'admin',
  'intelligence',
  'crm',
  'customer',
  'inventory',
  'orders',
  'procurement',
  'purchase',
  'invoice',
  'payments',
  'settings',
] as const;

const LOCALES = ['en', 'zh-Hant'] as const;

function getLocalesDir(): string {
  return path.resolve(process.cwd(), 'public', 'locales');
}

function getNamespacesForLocale(locale: string): Set<string> {
  const localeDir = path.join(getLocalesDir(), locale);
  const namespaces = new Set<string>();
  
  if (!fs.existsSync(localeDir)) {
    return namespaces;
  }
  
  const files = fs.readdirSync(localeDir);
  for (const file of files) {
    if (file.endsWith('.json')) {
      namespaces.add(file.replace('.json', ''));
    }
  }
  
  return namespaces;
}

describe('Locale Parity', () => {
  describe('Namespace Existence', () => {
    for (const locale of LOCALES) {
      for (const ns of REQUIRED_NAMESPACES) {
        const filePath = path.join(getLocalesDir(), locale, `${ns}.json`);
        
        it(`should have ${ns}.json in ${locale} locale`, () => {
          expect(fs.existsSync(filePath)).toBe(true);
        });
      }
    }
  });
  
  describe('Namespace Inventory Match', () => {
    it('should have matching namespace inventories between en and zh-Hant', () => {
      const enNamespaces = getNamespacesForLocale('en');
      const zhNamespaces = getNamespacesForLocale('zh-Hant');
      
      // Check en namespaces exist in zh-Hant
      for (const ns of enNamespaces) {
        expect(zhNamespaces.has(ns)).toBe(true);
      }
      
      // Check zh-Hant namespaces exist in en
      for (const ns of zhNamespaces) {
        expect(enNamespaces.has(ns)).toBe(true);
      }
    });
  });
  
  describe('JSON Validity', () => {
    for (const locale of LOCALES) {
      const localeDir = path.join(getLocalesDir(), locale);
      
      if (!fs.existsSync(localeDir)) {
        continue;
      }
      
      const files = fs.readdirSync(localeDir);
      const jsonFiles = files.filter(f => f.endsWith('.json'));
      
      for (const file of jsonFiles) {
        const filePath = path.join(localeDir, file);
        const ns = file.replace('.json', '');
        
        it(`should have valid JSON in ${locale}/${ns}`, () => {
          const content = fs.readFileSync(filePath, 'utf-8');
          expect(() => JSON.parse(content)).not.toThrow();
        });
      }
    }
  });
});
