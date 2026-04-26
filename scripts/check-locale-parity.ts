#!/usr/bin/env npx ts-node
/**
 * Locale Parity / Hygiene Check Script
 *
 * Validates that:
 * 1. All namespaces exist in both 'en' and 'zh-Hant' locales
 * 2. Namespace inventories match between locales
 * 3. Key counts are similar between locales (within threshold)
 * 4. All JSON files are valid
 *
 * Exit codes:
 * - 0: All checks passed
 * - 1: Validation failed
 */

import * as fs from 'fs';
import * as path from 'path';

// Namespace and locale constants (mirrored from src/lib/i18n-namespaces.ts)
const I18N_NAMESPACES = [
  'common', 'shell', 'routes', 'auth', 'dashboard',
  'admin', 'intelligence', 'crm', 'customer', 'inventory',
  'orders', 'procurement', 'purchase', 'invoice', 'payments', 'settings',
] as const;

const SUPPORTED_LOCALES = ['en', 'zh-Hant'] as const;

type Namespace = typeof I18N_NAMESPACES[number];
type Locale = typeof SUPPORTED_LOCALES[number];

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

function getLocalesDir(): string {
  return path.resolve(process.cwd(), 'public', 'locales');
}

function getNamespacesForLocale(locale: Locale): Set<string> {
  const localeDir = path.join(getLocalesDir(), locale);
  if (!fs.existsSync(localeDir)) return new Set();

  return new Set(
    fs.readdirSync(localeDir)
      .filter(f => f.endsWith('.json'))
      .map(f => f.replace('.json', ''))
  );
}

function countLeafKeys(obj: unknown): number {
  if (typeof obj !== 'object' || obj === null) return 0;

  let count = 0;
  const stack = [obj];

  while (stack.length) {
    const current = stack.pop();
    if (typeof current !== 'object' || current === null) continue;

    for (const [key, value] of Object.entries(current)) {
      void key;
      if (typeof value !== 'object' || value === null || Array.isArray(value)) {
        count++;
      } else {
        stack.push(value);
      }
    }
  }

  return count;
}

function validate(): ValidationResult {
  const result: ValidationResult = { valid: true, errors: [], warnings: [] };
  const enNs = getNamespacesForLocale('en');
  const zhNs = getNamespacesForLocale('zh-Hant');
  const KEY_RATIO_THRESHOLD = 2;

  // Check all namespaces exist
  for (const locale of SUPPORTED_LOCALES) {
    const namespaces = getNamespacesForLocale(locale);
    for (const ns of I18N_NAMESPACES) {
      if (!namespaces.has(ns)) {
        result.errors.push(`Missing namespace '${ns}' in '${locale}'`);
        result.valid = false;
      }
    }
  }

  // Check namespace parity
  for (const ns of enNs) {
    if (!zhNs.has(ns)) {
      result.errors.push(`Namespace '${ns}' in 'en' but not 'zh-Hant'`);
      result.valid = false;
    }
  }
  for (const ns of zhNs) {
    if (!enNs.has(ns)) {
      result.warnings.push(`Namespace '${ns}' in 'zh-Hant' but not 'en'`);
    }
  }

  // Validate JSON
  for (const locale of SUPPORTED_LOCALES) {
    const localeDir = path.join(getLocalesDir(), locale);
    if (!fs.existsSync(localeDir)) continue;

    for (const file of fs.readdirSync(localeDir)) {
      if (!file.endsWith('.json')) continue;

      const filePath = path.join(localeDir, file);
      try {
        JSON.parse(fs.readFileSync(filePath, 'utf-8'));
      } catch (e) {
        result.errors.push(`Invalid JSON in '${locale}/${file}': ${(e as Error).message}`);
        result.valid = false;
      }
    }
  }

  // Check key count parity
  for (const ns of I18N_NAMESPACES) {
    const enPath = path.join(getLocalesDir(), 'en', `${ns}.json`);
    const zhPath = path.join(getLocalesDir(), 'zh-Hant', `${ns}.json`);

    try {
      const enCount = countLeafKeys(JSON.parse(fs.readFileSync(enPath, 'utf-8')));
      const zhCount = countLeafKeys(JSON.parse(fs.readFileSync(zhPath, 'utf-8')));

      if (enCount === 0 && zhCount === 0) continue;

      const ratio = Math.max(enCount, zhCount) / Math.max(1, Math.min(enCount, zhCount));
      if (ratio > KEY_RATIO_THRESHOLD) {
        result.warnings.push(
          `Key count mismatch in '${ns}': en=${enCount}, zh-Hant=${zhCount} (ratio: ${ratio.toFixed(1)}x)`
        );
      }
    } catch {
      // Skip files that can't be read
    }
  }

  return result;
}

function printReport(result: ValidationResult): void {
  console.log('\n=== Locale Parity Check Report ===\n');

  if (result.errors.length) {
    console.log('ERRORS:');
    result.errors.forEach(e => console.log(`  ✗ ${e}`));
    console.log();
  }

  if (result.warnings.length) {
    console.log('WARNINGS:');
    result.warnings.forEach(w => console.log(`  ⚠ ${w}`));
    console.log();
  }

  if (result.valid) {
    console.log('✓ All locale parity checks passed!');
    console.log(`  - ${I18N_NAMESPACES.length} namespaces validated`);
    console.log(`  - ${SUPPORTED_LOCALES.length} locales checked (${SUPPORTED_LOCALES.join(', ')})`);
  } else {
    console.log('✗ Locale parity check FAILED');
    console.log(`  - ${result.errors.length} error(s), ${result.warnings.length} warning(s)`);
  }
  console.log();
}

// Main execution
const result = validate();
printReport(result);
process.exit(result.valid ? 0 : 1);
