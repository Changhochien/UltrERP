#!/usr/bin/env npx tsx
/**
 * i18n Validation Script
 * 
 * Checks for common i18n issues:
 * 1. Pages using 'common' namespace for domain keys
 * 2. Hardcoded English strings in JSX
 * 3. Missing namespace registrations
 * 
 * Run: pnpm validate:i18n
 */

import { readFileSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const SRC = join(ROOT, 'src');
const LOCALES = join(ROOT, 'public', 'locales');

// Issue counters
const issues: { type: string; file: string; line: string; message: string }[] = [];

// Check for pages using wrong namespace
function checkPageNamespaces() {
  const pages = readdirSync(join(SRC, 'pages'), { recursive: true })
    .filter(f => String(f).endsWith('.tsx') && !String(f).includes('.test.'));

  for (const page of pages) {
    const filepath = join(SRC, 'pages', String(page));
    const content = readFileSync(filepath, 'utf-8');
    const lines = content.split('\n');

    // Check for useTranslation("common") in domain pages
    const domainMatch = String(page).match(/pages\/(crm|customer|inventory|orders|invoice|accounting|procurement)/);
    if (domainMatch) {
      const domain = domainMatch[1];
      lines.forEach((line, i) => {
        if (line.includes('useTranslation("common")') && !line.includes('tCommon')) {
          issues.push({
            type: 'NAMESPACE',
            file: String(page),
            line: `L${i + 1}`,
            message: `Page uses 'common' namespace but should use '${domain}' for domain keys`
          });
        }
      });
    }

    // Check for hardcoded English strings
    const englishPatterns = [
      /[>:]\s*['"][A-Z][a-z]+ [A-Z][a-z]+/,
      /placeholder=\{['"][A-Z]/,
      /<option[^>]*>[A-Z]/,
    ];

    lines.forEach((line, i) => {
      // Skip comments and imports
      if (line.trim().startsWith('//') || line.trim().startsWith('*') || line.includes('import')) return;
      
      // Check for likely hardcoded English
      if (/>(Select|Create|Edit|Delete|View|Add|Update|Remove)[^<]*</.test(line)) {
        issues.push({
          type: 'HARDCODED',
          file: String(page),
          line: `L${i + 1}`,
          message: `Possible hardcoded English string: ${line.trim().substring(0, 60)}...`
        });
      }
    });
  }
}

// Check for missing namespace files
function checkNamespaceFiles() {
  const namespacesPath = join(SRC, 'lib', 'i18n-namespaces.ts');
  const namespacesContent = readFileSync(namespacesPath, 'utf-8');
  const definedNamespaces = namespacesContent.match(/'([a-z]+)'/g) || [];
  
  const localeFiles = readdirSync(join(LOCALES, 'en'));
  
  for (const file of localeFiles) {
    if (file.endsWith('.json')) {
      const ns = file.replace('.json', '');
      if (!definedNamespaces.includes(`'${ns}'`)) {
        issues.push({
          type: 'MISSING_NS',
          file: `public/locales/en/${file}`,
          line: '-',
          message: `Namespace '${ns}' used in locale files but not registered in i18n-namespaces.ts`
        });
      }
    }
  }
}

// Run checks
console.log('🔍 Validating i18n architecture...\n');

checkPageNamespaces();
checkNamespaceFiles();

// Report
if (issues.length === 0) {
  console.log('✅ No i18n issues found!\n');
} else {
  console.log(`⚠️  Found ${issues.length} issues:\n`);
  
  const byType = issues.reduce((acc, issue) => {
    acc[issue.type] = acc[issue.type] || [];
    acc[issue.type].push(issue);
    return acc;
  }, {} as Record<string, typeof issues>);

  for (const [type, typeIssues] of Object.entries(byType)) {
    console.log(`\n📋 ${type} (${typeIssues.length}):`);
    for (const issue of typeIssues.slice(0, 10)) {
      console.log(`   ${issue.file}:${issue.line} - ${issue.message}`);
    }
    if (typeIssues.length > 10) {
      console.log(`   ... and ${typeIssues.length - 10} more`);
    }
  }
  console.log();
}

process.exit(issues.length > 0 ? 1 : 0);
