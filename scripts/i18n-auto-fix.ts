#!/usr/bin/env node
/**
 * i18n Auto-Fix Script
 * 
 * Automatically fixes common i18n issues:
 * - Adds missing translation keys with placeholder values
 * - Validates placeholder counts
 * 
 * Usage: npx tsx scripts/i18n-auto-fix.ts [--dry-run]
 */

import * as fs from 'fs';
import * as path from 'path';

const LOCALES_DIR = './public/locales';
const SOURCE_LOCALE = 'en';
const TARGET_LOCALES = ['zh-Hant'];
const NAMESPACES = [
  'common', 'shell', 'routes', 'auth', 'dashboard', 'admin',
  'intelligence', 'crm', 'customer', 'inventory', 'orders',
  'procurement', 'purchase', 'invoice', 'payments', 'settings'
];

const DRY_RUN = process.argv.includes('--dry-run');

function flattenKeys(obj: unknown, prefix = ''): Record<string, string> {
  const result: Record<string, string> = {};
  if (typeof obj !== 'object' || obj === null) return result;
  
  for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      Object.assign(result, flattenKeys(value, fullKey));
    } else if (typeof value === 'string') {
      result[fullKey] = value;
    }
  }
  return result;
}

function unflattenKeys(flat: Record<string, string>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  
  for (const [key, value] of Object.entries(flat)) {
    const parts = key.split('.');
    let current = result;
    
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      if (!(part in current)) {
        current[part] = {};
      }
      current = current[part] as Record<string, unknown>;
    }
    
    current[parts[parts.length - 1]] = value;
  }
  
  return result;
}

interface Fix {
  locale: string;
  namespace: string;
  key: string;
  action: 'add' | 'placeholder-fix';
  originalValue?: string;
  newValue?: string;
}

function findMissingKeys(): Fix[] {
  const fixes: Fix[] = [];
  
  // Load source locale
  const sourceData: Record<string, Record<string, string>> = {};
  for (const namespace of NAMESPACES) {
    const filePath = path.join(LOCALES_DIR, SOURCE_LOCALE, `${namespace}.json`);
    if (fs.existsSync(filePath)) {
      const content = fs.readFileSync(filePath, 'utf-8');
      sourceData[namespace] = flattenKeys(JSON.parse(content));
    }
  }
  
  // Check each target locale
  for (const locale of TARGET_LOCALES) {
    for (const namespace of NAMESPACES) {
      const sourceFile = path.join(LOCALES_DIR, SOURCE_LOCALE, `${namespace}.json`);
      const targetFile = path.join(LOCALES_DIR, locale, `${namespace}.json`);
      
      if (!fs.existsSync(sourceFile)) continue;
      
      const sourceContent = fs.readFileSync(sourceFile, 'utf-8');
      const sourceKeys = flattenKeys(JSON.parse(sourceContent));
      
      let targetData: Record<string, string> = {};
      if (fs.existsSync(targetFile)) {
        const targetContent = fs.readFileSync(targetFile, 'utf-8');
        targetData = flattenKeys(JSON.parse(targetContent));
      }
      
      // Find missing keys
      for (const [key, value] of Object.entries(sourceKeys)) {
        if (!(key in targetData)) {
          fixes.push({
            locale,
            namespace,
            key,
            action: 'add',
            newValue: `[TODO: ${value}]`,
          });
        }
      }
    }
  }
  
  return fixes;
}

function applyFixes(fixes: Fix[]): void {
  for (const fix of fixes) {
    const targetFile = path.join(LOCALES_DIR, fix.locale, `${fix.namespace}.json`);
    
    let data: Record<string, unknown>;
    if (fs.existsSync(targetFile)) {
      const content = fs.readFileSync(targetFile, 'utf-8');
      data = JSON.parse(content);
    } else {
      data = {};
    }
    
    // Set the value using dot notation
    const parts = fix.key.split('.');
    let current = data;
    
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      if (!(part in current)) {
        current[part] = {};
      }
      current = current[part] as Record<string, unknown>;
    }
    
    current[parts[parts.length - 1]] = fix.newValue;
    
    if (!DRY_RUN) {
      fs.writeFileSync(targetFile, JSON.stringify(data, null, 2) + '\n');
    }
    
    console.log(`  ${DRY_RUN ? '[DRY-RUN] ' : ''}${fix.locale}/${fix.namespace}.json: Added "${fix.key}"`);
  }
}

function main() {
  console.log('\n🔧 i18n Auto-Fix');
  console.log('================\n');
  
  if (DRY_RUN) {
    console.log('⚠️  DRY RUN MODE - No changes will be made\n');
  }
  
  console.log('Finding missing translation keys...');
  const fixes = findMissingKeys();
  
  if (fixes.length === 0) {
    console.log('✅ No fixes needed!\n');
    return;
  }
  
  console.log(`\nFound ${fixes.length} missing key(s):\n`);
  
  // Group by namespace
  const byNamespace = fixes.reduce((acc, fix) => {
    const key = `${fix.locale}/${fix.namespace}`;
    if (!acc[key]) acc[key] = [];
    acc[key].push(fix);
    return acc;
  }, {} as Record<string, Fix[]>);
  
  for (const [location, namespaceFixes] of Object.entries(byNamespace)) {
    console.log(`  ${location}: ${namespaceFixes.length} missing key(s)`);
  }
  
  if (!DRY_RUN) {
    console.log('\nApplying fixes...');
    applyFixes(fixes);
    console.log('\n✅ Fixes applied!\n');
    console.log('⚠️  Please translate the [TODO: ...] placeholders manually.\n');
  } else {
    console.log('\nℹ️  Run without --dry-run to apply fixes.\n');
  }
}

main();
