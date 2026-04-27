#!/usr/bin/env node
/**
 * i18n Validation Script
 * 
 * Usage: npx tsx scripts/i18n-validate.ts
 * 
 * Checks for:
 * 1. Missing translations between locales
 * 2. Malformed JSON
 * 3. Inconsistent placeholder count
 * 4. Unused or orphaned keys
 */

import * as fs from 'fs';
import * as path from 'path';
import * as glob from 'glob';

const LOCALES_DIR = './public/locales';
const LOCALES = ['en', 'zh-Hant'];
const NAMESPACES = [
  'common', 'shell', 'routes', 'auth', 'dashboard', 'admin',
  'intelligence', 'crm', 'customer', 'inventory', 'orders',
  'procurement', 'purchase', 'invoice', 'payments', 'settings'
];

interface ValidationResult {
  file: string;
  errors: string[];
  warnings: string[];
}

function flattenKeys(obj: any, prefix = ''): Record<string, any> {
  const result: Record<string, any> = {};
  for (const key in obj) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
      Object.assign(result, flattenKeys(obj[key], fullKey));
    } else {
      result[fullKey] = obj[key];
    }
  }
  return result;
}

function extractPlaceholders(value: string): string[] {
  const matches = value.match(/\{\{[^}]+\}\}|\{[^}]+\}/g) || [];
  return matches;
}

function validateJson(filePath: string): { valid: boolean; error?: string } {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    JSON.parse(content);
    return { valid: true };
  } catch (e: any) {
    return { valid: false, error: e.message };
  }
}

function validateNamespace(namespace: string): ValidationResult[] {
  const results: ValidationResult[] = [];
  
  for (const locale of LOCALES) {
    const filePath = path.join(LOCALES_DIR, locale, `${namespace}.json`);
    const result: ValidationResult = {
      file: `${locale}/${namespace}`,
      errors: [],
      warnings: []
    };

    // Check if file exists
    if (!fs.existsSync(filePath)) {
      result.errors.push(`File not found: ${filePath}`);
      results.push(result);
      continue;
    }

    // Validate JSON syntax
    const jsonCheck = validateJson(filePath);
    if (!jsonCheck.valid) {
      result.errors.push(`Invalid JSON: ${jsonCheck.error}`);
      results.push(result);
      continue;
    }

    const content = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    const flat = flattenKeys(content);

    // Check for empty values
    for (const [key, value] of Object.entries(flat)) {
      if (value === '' || value === null) {
        result.warnings.push(`Empty value for key: ${key}`);
      }
      
      // Check placeholder consistency
      const enFilePath = path.join(LOCALES_DIR, 'en', `${namespace}.json`);
      if (fs.existsSync(enFilePath)) {
        const enContent = JSON.parse(fs.readFileSync(enFilePath, 'utf-8'));
        const enFlat = flattenKeys(enContent);
        
        if (locale !== 'en' && enFlat[key] !== undefined) {
          const enPlaceholders = extractPlaceholders(String(enFlat[key]));
          const localePlaceholders = extractPlaceholders(String(value));
          
          if (enPlaceholders.length !== localePlaceholders.length) {
            result.warnings.push(
              `Placeholder mismatch for ${key}: en=${enPlaceholders.length}, ${locale}=${localePlaceholders.length}`
            );
          }
        }
      }
    }

    if (result.errors.length > 0 || result.warnings.length > 0) {
      results.push(result);
    }
  }

  // Compare keys between locales
  const enFile = path.join(LOCALES_DIR, 'en', `${namespace}.json`);
  const zhFile = path.join(LOCALES_DIR, 'zh-Hant', `${namespace}.json`);
  
  if (fs.existsSync(enFile) && fs.existsSync(zhFile)) {
    const enContent = JSON.parse(fs.readFileSync(enFile, 'utf-8'));
    const zhContent = JSON.parse(fs.readFileSync(zhFile, 'utf-8'));
    
    const enKeys = new Set(Object.keys(flattenKeys(enContent)));
    const zhKeys = new Set(Object.keys(flattenKeys(zhContent)));

    const missingInZh = [...enKeys].filter(k => !zhKeys.has(k));
    const missingInEn = [...zhKeys].filter(k => !enKeys.has(k));

    if (missingInZh.length > 0) {
      console.log(`\n⚠️  ${namespace}: Missing in zh-Hant (${missingInZh.length})`);
      missingInZh.slice(0, 5).forEach(k => console.log(`   - ${k}`));
      if (missingInZh.length > 5) console.log(`   ... and ${missingInZh.length - 5} more`);
    }

    if (missingInEn.length > 0) {
      console.log(`\n⚠️  ${namespace}: Extra in zh-Hant (${missingInEn.length})`);
      missingInEn.slice(0, 5).forEach(k => console.log(`   + ${k}`));
    }
  }

  return results;
}

function main() {
  console.log('🔍 i18n Validation Report');
  console.log('========================\n');

  let totalErrors = 0;
  let totalWarnings = 0;

  for (const namespace of NAMESPACES) {
    const results = validateNamespace(namespace);
    for (const result of results) {
      totalErrors += result.errors.length;
      totalWarnings += result.warnings.length;
      
      if (result.errors.length > 0) {
        console.log(`\n❌ ${result.file}:`);
        result.errors.forEach(e => console.log(`   ${e}`));
      }
      if (result.warnings.length > 0) {
        console.log(`\n⚠️  ${result.file}:`);
        result.warnings.forEach(w => console.log(`   ${w}`));
      }
    }
  }

  console.log('\n========================');
  console.log(`Summary: ${totalErrors} errors, ${totalWarnings} warnings`);
  
  if (totalErrors > 0) {
    process.exit(1);
  }
}

main();
