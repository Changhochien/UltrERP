/**
 * ESLint Plugin for i18n Validation
 * 
 * Rules:
 * - no-missing-translation-key: Ensures all translation keys exist in all locales
 * - no-untranslated-key: Ensures no keys exist in non-source locales that aren't in source
 * - require-description: Ensures certain keys have descriptions
 * 
 * Usage in eslint.config.js:
 *   import { rules as i18nRules } from './eslint/rules/i18n.js';
 *   { rules: { ...i18nRules } }
 */

const fs = require('fs');
const path = require('path');

const LOCALES_DIR = path.join(process.cwd(), 'public', 'locales');
const SOURCE_LOCALE = 'en';
const NAMESPACES = [
  'common', 'shell', 'routes', 'auth', 'dashboard', 'admin',
  'intelligence', 'crm', 'customer', 'inventory', 'orders',
  'procurement', 'purchase', 'invoice', 'payments', 'settings'
];

/**
 * Load all translation keys from a locale
 */
function loadLocaleKeys(locale) {
  const keys = {};
  for (const namespace of NAMESPACES) {
    const filePath = path.join(LOCALES_DIR, locale, `${namespace}.json`);
    if (fs.existsSync(filePath)) {
      try {
        const content = fs.readFileSync(filePath, 'utf-8');
        const parsed = JSON.parse(content);
        keys[namespace] = flattenKeys(parsed);
      } catch (e) {
        console.error(`Error loading ${locale}/${namespace}.json:`, e.message);
      }
    }
  }
  return keys;
}

/**
 * Flatten nested object to dot-notation keys
 */
function flattenKeys(obj, prefix = '') {
  const result = {};
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      Object.assign(result, flattenKeys(value, fullKey));
    } else {
      result[fullKey] = value;
    }
  }
  return result;
}

// Cache loaded locales
let cachedLocales = null;

function getLocales() {
  if (!cachedLocales) {
    cachedLocales = {
      [SOURCE_LOCALE]: loadLocaleKeys(SOURCE_LOCALE),
    };
    // Load other locales lazily
  }
  return cachedLocales;
}

/**
 * Rule: no-missing-translation-key
 * Reports when a translation key exists in source locale but not in target locales
 */
function noMissingTranslationKey(context) {
  const sourceKeys = loadLocaleKeys(SOURCE_LOCALE);
  
  return {
    Program(node) {
      const locales = fs.readdirSync(path.join(LOCALES_DIR))
        .filter(f => f !== SOURCE_LOCALE && fs.statSync(path.join(LOCALES_DIR, f)).isDirectory());
      
      for (const locale of locales) {
        const targetKeys = loadLocaleKeys(locale);
        
        for (const [namespace, keys] of Object.entries(sourceKeys)) {
          if (!targetKeys[namespace]) continue;
          
          for (const [key] of Object.entries(keys)) {
            if (!(key in targetKeys[namespace])) {
              context.report({
                node,
                message: `Missing translation in ${locale}/${namespace}: "${key}"`,
                data: { locale, namespace, key },
              });
            }
          }
        }
      }
    },
  };
}

/**
 * Rule: validate-placeholder-count
 * Reports when placeholder counts don't match between locales
 */
function validatePlaceholderCount(context) {
  const sourceKeys = loadLocaleKeys(SOURCE_LOCALE);
  
  function extractPlaceholders(value) {
    return (value.match(/\{\{[^}]+\}\}|\{[^}]+\}/g) || []).length;
  }
  
  return {
    Program(node) {
      const locales = fs.readdirSync(path.join(LOCALES_DIR))
        .filter(f => f !== SOURCE_LOCALE && fs.statSync(path.join(LOCALES_DIR, f)).isDirectory());
      
      for (const locale of locales) {
        const targetKeys = loadLocaleKeys(locale);
        
        for (const [namespace, keys] of Object.entries(sourceKeys)) {
          if (!targetKeys[namespace]) continue;
          
          for (const [key, value] of Object.entries(keys)) {
            const targetValue = targetKeys[namespace][key];
            if (!targetValue || typeof targetValue !== 'string') continue;
            
            const sourceCount = extractPlaceholders(value);
            const targetCount = extractPlaceholders(targetValue);
            
            if (sourceCount !== targetCount) {
              context.report({
                node,
                message: `Placeholder mismatch in ${locale}/${namespace}.${key}: expected ${sourceCount}, got ${targetCount}`,
                data: { locale, namespace, key, expected: sourceCount, actual: targetCount },
              });
            }
          }
        }
      }
    },
  };
}

/**
 * Rule: no-empty-translations
 * Reports when translations are empty strings
 */
function noEmptyTranslations(context) {
  return {
    Program(node) {
      const locales = fs.readdirSync(path.join(LOCALES_DIR))
        .filter(f => fs.statSync(path.join(LOCALES_DIR, f)).isDirectory());
      
      for (const locale of locales) {
        const keys = loadLocaleKeys(locale);
        
        for (const [namespace, nsKeys] of Object.entries(keys)) {
          for (const [key, value] of Object.entries(nsKeys)) {
            if (value === '' || value === null) {
              context.report({
                node,
                message: `Empty translation in ${locale}/${namespace}.${key}`,
                data: { locale, namespace, key },
              });
            }
          }
        }
      }
    },
  };
}

module.exports = {
  rules: {
    'no-missing-translation-key': {
      create: noMissingTranslationKey,
      meta: {
        type: 'problem',
        docs: {
          description: 'Ensures all translation keys exist in all locales',
          recommended: 'error',
        },
        fixable: null,
      },
    },
    'validate-placeholder-count': {
      create: validatePlaceholderCount,
      meta: {
        type: 'problem',
        docs: {
          description: 'Ensures placeholder counts match between locales',
          recommended: 'error',
        },
        fixable: null,
      },
    },
    'no-empty-translations': {
      create: noEmptyTranslations,
      meta: {
        type: 'problem',
        docs: {
          description: 'Ensures no translations are empty strings',
          recommended: 'error',
        },
        fixable: null,
      },
    },
  },
  configs: {
    recommended: {
      plugins: ['i18n'],
      rules: {
        'i18n/no-missing-translation-key': 'error',
        'i18n/validate-placeholder-count': 'warn',
        'i18n/no-empty-translations': 'error',
      },
    },
  },
};
