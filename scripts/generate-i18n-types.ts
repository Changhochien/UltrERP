#!/usr/bin/env node
/**
 * i18n Type Generator Script
 * 
 * Generates TypeScript type definitions from locale JSON files.
 * Run: npx tsx scripts/generate-i18n-types.ts
 * 
 * Features:
 * - Extracts all translation keys from JSON files
 * - Generates type definitions for type-safe translations
 * - Validates key consistency across locales
 * - Creates autocomplete hints
 */

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

const LOCALES_DIR = './public/locales';
const OUTPUT_FILE = './src/lib/i18n/generated-keys.ts';
const MANIFEST_FILE = './src/lib/i18n/locale-manifest.json';
const LOCALES = ['en', 'zh-Hant'];
const NAMESPACES = [
  'common', 'shell', 'routes', 'auth', 'dashboard', 'admin',
  'intelligence', 'crm', 'customer', 'inventory', 'orders',
  'procurement', 'purchase', 'invoice', 'payments', 'settings'
];

// =============================================================================
// UTILITIES
// =============================================================================

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

function extractPlaceholders(value: string): string[] {
  return value.match(/\{\{[^}]+\}\}|\{[^}]+\}/g) || [];
}

function computeHash(content: string): string {
  return crypto.createHash('md5').update(content).digest('hex');
}

// =============================================================================
// VALIDATION
// =============================================================================

interface ValidationIssue {
  severity: 'error' | 'warning';
  namespace: string;
  locale?: string;
  message: string;
  key?: string;
}

function validateTranslationFiles(): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  
  // Load English as reference
  const enKeys: Record<string, string>[] = [];
  for (const namespace of NAMESPACES) {
    const filePath = path.join(LOCALES_DIR, 'en', `${namespace}.json`);
    if (fs.existsSync(filePath)) {
      const content = fs.readFileSync(filePath, 'utf-8');
      const parsed = JSON.parse(content);
      enKeys[namespace] = flattenKeys(parsed);
    }
  }
  
  // Check each target locale
  for (const locale of LOCALES.filter(l => l !== 'en')) {
    for (const namespace of NAMESPACES) {
      const filePath = path.join(LOCALES_DIR, locale, `${namespace}.json`);
      
      if (!fs.existsSync(filePath)) {
        issues.push({
          severity: 'error',
          namespace,
          locale,
          message: `Missing translation file: ${locale}/${namespace}.json`,
        });
        continue;
      }
      
      try {
        const content = fs.readFileSync(filePath, 'utf-8');
        const parsed = JSON.parse(content);
        const localeKeys = flattenKeys(parsed);
        const referenceKeys = enKeys[namespace] || {};
        
        // Check for missing keys
        for (const [key, value] of Object.entries(referenceKeys)) {
          if (!(key in localeKeys)) {
            issues.push({
              severity: 'error',
              namespace,
              locale,
              key,
              message: `Missing translation: "${key}"`,
            });
          } else {
            // Check placeholder parity
            const refPlaceholders = extractPlaceholders(value);
            const localePlaceholders = extractPlaceholders(localeKeys[key]);
            
            if (refPlaceholders.length !== localePlaceholders.length) {
              issues.push({
                severity: 'warning',
                namespace,
                locale,
                key,
                message: `Placeholder count mismatch: ${refPlaceholders.length} vs ${localePlaceholders.length}`,
              });
            }
            
            // Check for empty values
            if (localeKeys[key] === '') {
              issues.push({
                severity: 'warning',
                namespace,
                locale,
                key,
                message: `Empty translation value`,
              });
            }
          }
        }
        
        // Check for extra keys
        for (const key of Object.keys(localeKeys)) {
          if (!(key in referenceKeys)) {
            issues.push({
              severity: 'warning',
              namespace,
              locale,
              key,
              message: `Extra key not in reference locale`,
            });
          }
        }
      } catch (e) {
        issues.push({
          severity: 'error',
          namespace,
          locale,
          message: `Invalid JSON: ${e}`,
        });
      }
    }
  }
  
  return issues;
}

// =============================================================================
// TYPE GENERATION
// =============================================================================

function generateTypeDefinitions(): string {
  const allKeys: Record<string, string[]> = {};
  
  // Collect all keys from English locale (source of truth)
  for (const namespace of NAMESPACES) {
    const filePath = path.join(LOCALES_DIR, 'en', `${namespace}.json`);
    if (fs.existsSync(filePath)) {
      const content = fs.readFileSync(filePath, 'utf-8');
      const parsed = JSON.parse(content);
      const keys = flattenKeys(parsed);
      allKeys[namespace] = Object.keys(keys);
    }
  }
  
  const namespaceTypes = NAMESPACES.map(ns => {
    const keys = allKeys[ns] || [];
    const keyLiterals = keys.map(k => `  | "${k}"`).join('\n');
    return `export type ${toPascalCase(ns)}Keys = \n${keyLiterals}\n  | never;`;
  });
  
  return `/**
 * AUTO-GENERATED i18n Type Definitions
 * Generated: ${new Date().toISOString()}
 * 
 * DO NOT EDIT MANUALLY
 * Run: pnpm generate:i18n-types
 */

import { NAMESPACES } from './namespaces';

// =============================================================================
// NAMESPACE KEY TYPES
// =============================================================================

${namespaceTypes.join('\n\n')}

// =============================================================================
// ALL KEYS UNION TYPE
// =============================================================================

export type AllTranslationKeys = ${NAMESPACES.map(ns => toPascalCase(ns) + 'Keys').join(' | ')};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

function toNamespaceKey(namespace: string, key: string): string {
  return key;
}

// Type-safe translation key builder
export function createTranslationKey<
  N extends keyof typeof NAMESPACES,
  K extends string
>(namespace: N, key: K): \`\${typeof NAMESPACES[N]}.\${K}\` {
  return \`\${NAMESPACES[N]}.\${key}\` as \`\${typeof NAMESPACES[N]}.\${K}\`;
}
`;
}

function toPascalCase(str: string): string {
  return str
    .split(/[-_]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join('');
}

// =============================================================================
// MANIFEST GENERATION
// =============================================================================

function generateManifest(): void {
  const manifest: Record<string, { keys: string[]; hash: string; lastModified: string }> = {};
  
  for (const namespace of NAMESPACES) {
    const filePath = path.join(LOCALES_DIR, 'en', `${namespace}.json`);
    if (fs.existsSync(filePath)) {
      const content = fs.readFileSync(filePath, 'utf-8');
      const parsed = JSON.parse(content);
      const keys = Object.keys(flattenKeys(parsed));
      
      manifest[namespace] = {
        keys,
        hash: computeHash(content),
        lastModified: fs.statSync(filePath).mtime.toISOString(),
      };
    }
  }
  
  fs.writeFileSync(MANIFEST_FILE, JSON.stringify(manifest, null, 2));
  console.log(`📋 Manifest generated: ${MANIFEST_FILE}`);
}

// =============================================================================
// MAIN
// =============================================================================

function main() {
  console.log('\n🔧 i18n Type Generator');
  console.log('======================\n');
  
  // Validate first
  console.log('📋 Validating translation files...');
  const issues = validateTranslationFiles();
  
  const errors = issues.filter(i => i.severity === 'error');
  const warnings = issues.filter(i => i.severity === 'warning');
  
  if (errors.length > 0) {
    console.log('\n❌ Validation Errors:');
    errors.forEach(e => {
      const location = e.locale ? `${e.locale}/${e.namespace}` : e.namespace;
      console.log(`   ${location}: ${e.message}${e.key ? ` (${e.key})` : ''}`);
    });
  }
  
  if (warnings.length > 0) {
    console.log('\n⚠️  Validation Warnings:');
    warnings.slice(0, 20).forEach(e => {
      const location = e.locale ? `${e.locale}/${e.namespace}` : e.namespace;
      console.log(`   ${location}: ${e.message}${e.key ? ` (${e.key})` : ''}`);
    });
    if (warnings.length > 20) {
      console.log(`   ... and ${warnings.length - 20} more warnings`);
    }
  }
  
  if (errors.length > 0) {
    console.log('\n❌ Cannot generate types - validation errors found.\n');
    process.exit(1);
  }
  
  // Generate types
  console.log('\n📝 Generating type definitions...');
  const types = generateTypeDefinitions();
  fs.writeFileSync(OUTPUT_FILE, types);
  console.log(`✅ Types generated: ${OUTPUT_FILE}`);
  
  // Generate manifest
  console.log('\n📋 Generating locale manifest...');
  generateManifest();
  
  if (warnings.length > 0) {
    console.log(`\n⚠️  Generated with ${warnings.length} warning(s).\n`);
  } else {
    console.log('\n✅ All validations passed!\n');
  }
}

main();
