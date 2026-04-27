#!/usr/bin/env node
/**
 * i18n Coverage Report Generator
 * 
 * Generates a JSON report of translation coverage across all locales.
 * Usage: npx tsx scripts/i18n-coverage.ts
 */

import * as fs from 'fs';
import * as path from 'path';

const LOCALES_DIR = './public/locales';
const OUTPUT_FILE = './i18n-coverage-report.json';
const LOCALES = ['en', 'zh-Hant'];
const NAMESPACES = [
  'common', 'shell', 'routes', 'auth', 'dashboard', 'admin',
  'intelligence', 'crm', 'customer', 'inventory', 'orders',
  'procurement', 'purchase', 'invoice', 'payments', 'settings'
];

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

function loadLocaleData(locale: string): Record<string, Record<string, string>> {
  const data: Record<string, Record<string, string>> = {};
  for (const namespace of NAMESPACES) {
    const filePath = path.join(LOCALES_DIR, locale, `${namespace}.json`);
    if (fs.existsSync(filePath)) {
      const content = fs.readFileSync(filePath, 'utf-8');
      const parsed = JSON.parse(content);
      data[namespace] = flattenKeys(parsed);
    }
  }
  return data;
}

interface CoverageReport {
  generated: string;
  locales: Array<{
    locale: string;
    total: number;
    translated: number;
    coverage: number;
  }>;
  namespaces: Array<{
    name: string;
    total: number;
    byLocale: Record<string, number>;
  }>;
  issues: Array<{
    namespace: string;
    key: string;
    locale: string;
    message: string;
  }>;
}

function main() {
  console.log('\n📊 i18n Coverage Report Generator\n');
  
  const report: CoverageReport = {
    generated: new Date().toISOString(),
    locales: [],
    namespaces: [],
    issues: [],
  };
  
  // Load all locales
  const allLocaleData: Record<string, Record<string, Record<string, string>>> = {};
  for (const locale of LOCALES) {
    allLocaleData[locale] = loadLocaleData(locale);
  }
  
  // Calculate per-locale coverage (using English as reference)
  const referenceKeys = allLocaleData['en'];
  const referenceTotal = Object.values(referenceKeys).reduce((sum, ns) => sum + Object.keys(ns).length, 0);
  
  for (const locale of LOCALES) {
    let translated = 0;
    const localeData = allLocaleData[locale];
    
    for (const [namespace, keys] of Object.entries(referenceKeys)) {
      const localeKeys = localeData[namespace] || {};
      
      for (const [key, value] of Object.entries(keys)) {
        if (localeKeys[key] !== undefined && localeKeys[key] !== '') {
          translated++;
        } else if (locale !== 'en') {
          report.issues.push({
            namespace,
            key,
            locale,
            message: 'Missing translation',
          });
        }
      }
    }
    
    report.locales.push({
      locale,
      total: referenceTotal,
      translated: locale === 'en' ? referenceTotal : translated,
      coverage: (translated / referenceTotal) * 100,
    });
  }
  
  // Calculate per-namespace coverage
  for (const namespace of NAMESPACES) {
    let total = 0;
    const byLocale: Record<string, number> = {};
    
    for (const locale of LOCALES) {
      const keys = allLocaleData[locale][namespace] || {};
      byLocale[locale] = Object.keys(keys).length;
      total += Object.keys(keys).length;
    }
    
    report.namespaces.push({ name: namespace, total, byLocale });
  }
  
  // Write report
  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(report, null, 2));
  
  // Print summary
  console.log('Coverage by Locale:');
  console.log('------------------');
  for (const locale of report.locales) {
    const bar = '█'.repeat(Math.round(locale.coverage / 5)) + '░'.repeat(20 - Math.round(locale.coverage / 5));
    console.log(`${locale.locale.padEnd(10)} ${bar} ${locale.coverage.toFixed(1)}%`);
  }
  
  if (report.issues.length > 0) {
    console.log('\n⚠️  Issues Found:');
    const grouped = report.issues.reduce((acc, issue) => {
      const key = `${issue.locale}/${issue.namespace}`;
      if (!acc[key]) acc[key] = [];
      acc[key].push(issue.key);
      return acc;
    }, {} as Record<string, string[]>);
    
    for (const [location, keys] of Object.entries(grouped)) {
      console.log(`  ${location}: ${keys.length} missing keys`);
    }
  }
  
  console.log(`\n📄 Report saved to: ${OUTPUT_FILE}\n`);
}

main();
