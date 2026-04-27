#!/usr/bin/env node
/**
 * i18n Pre-commit Check
 * 
 * Run this script before commits to ensure translation integrity.
 * Usage: node scripts/i18n-check.ts
 * 
 * Add to .husky/pre-commit:
 *   npx tsx scripts/i18n-check.ts
 */

import * as fs from 'fs';
import * as path from 'path';

const LOCALES_DIR = './public/locales';
const LOCALES = ['en', 'zh-Hant'];
const NAMESPACES = [
  'common', 'shell', 'routes', 'auth', 'dashboard', 'admin',
  'intelligence', 'crm', 'customer', 'inventory', 'orders',
  'procurement', 'purchase', 'invoice', 'payments', 'settings'
];

interface Issue {
  type: 'error' | 'warning';
  message: string;
  file?: string;
}

const issues: Issue[] = [];

function flattenKeys(obj: unknown, prefix = ''): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  if (typeof obj !== 'object' || obj === null) return result;
  
  for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      Object.assign(result, flattenKeys(value, fullKey));
    } else {
      result[fullKey] = value;
    }
  }
  return result;
}

function extractPlaceholders(value: string): number {
  return (value.match(/\{\{[^}]+\}\}|\{[^}]+\}/g) || []).length;
}

// Check each namespace
for (const namespace of NAMESPACES) {
  const enFile = path.join(LOCALES_DIR, 'en', `${namespace}.json`);
  const zhFile = path.join(LOCALES_DIR, 'zh-Hant', `${namespace}.json`);
  
  if (!fs.existsSync(enFile)) {
    issues.push({ type: 'error', message: `Missing English file: ${namespace}.json` });
    continue;
  }
  
  if (!fs.existsSync(zhFile)) {
    issues.push({ type: 'error', message: `Missing Chinese file: ${namespace}.json` });
    continue;
  }
  
  // Validate JSON
  try {
    JSON.parse(fs.readFileSync(enFile, 'utf-8'));
    JSON.parse(fs.readFileSync(zhFile, 'utf-8'));
  } catch (e) {
    issues.push({ type: 'error', message: `Invalid JSON in ${namespace}.json` });
    continue;
  }
  
  const enContent = JSON.parse(fs.readFileSync(enFile, 'utf-8'));
  const zhContent = JSON.parse(fs.readFileSync(zhFile, 'utf-8'));
  
  const enKeys = flattenKeys(enContent);
  const zhKeys = flattenKeys(zhContent);
  
  // Check for missing keys
  for (const key of Object.keys(enKeys)) {
    if (!(key in zhKeys)) {
      issues.push({
        type: 'error',
        message: `Missing Chinese translation: ${namespace}.${key}`,
        file: `zh-Hant/${namespace}.json`
      });
    }
    
    // Check placeholders
    if (typeof enKeys[key] === 'string' && typeof zhKeys[key] === 'string') {
      const enPlaceholders = extractPlaceholders(enKeys[key] as string);
      const zhPlaceholders = extractPlaceholders(zhKeys[key] as string);
      
      if (enPlaceholders !== zhPlaceholders) {
        issues.push({
          type: 'warning',
          message: `Placeholder mismatch: ${namespace}.${key}`,
          file: `zh-Hant/${namespace}.json`
        });
      }
    }
    
    // Check for empty values
    if (zhKeys[key] === '' || zhKeys[key] === null) {
      issues.push({
        type: 'warning',
        message: `Empty Chinese translation: ${namespace}.${key}`,
        file: `zh-Hant/${namespace}.json`
      });
    }
  }
}

// Report
console.log('\n🔍 i18n Pre-commit Check');
console.log('========================\n');

const errors = issues.filter(i => i.type === 'error');
const warnings = issues.filter(i => i.type === 'warning');

if (warnings.length > 0) {
  console.log('⚠️  Warnings:');
  warnings.forEach(w => console.log(`   ${w.message}`));
  console.log('');
}

if (errors.length > 0) {
  console.log('❌ Errors (blocking commit):');
  errors.forEach(e => console.log(`   ${e.message}`));
  console.log('\n========================');
  console.log(`❌ ${errors.length} error(s) found. Please fix before committing.\n`);
  process.exit(1);
}

if (issues.length === 0) {
  console.log('✅ All translations are valid!\n');
  process.exit(0);
}

console.log('========================');
console.log(`⚠️  ${warnings.length} warning(s). Commit allowed but should be addressed.\n`);
process.exit(0);
