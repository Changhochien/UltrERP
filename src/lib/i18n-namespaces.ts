/**
 * i18n Namespace Constants
 *
 * Central definition of all translation namespaces and locales used across the application.
 * Import this in both runtime (i18n.ts) and test (tests/helpers/i18n.ts) configs
 * to ensure namespace consistency.
 */

export const I18N_NAMESPACES = [
  'common',
  'shell',
  'routes',
  'auth',
  'accounting',
  'dashboard',
  'manufacturing',
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

export type I18nNamespace = typeof I18N_NAMESPACES[number];

export const SUPPORTED_LOCALES = ['en', 'zh-Hant'] as const;
export type SupportedLocale = typeof SUPPORTED_LOCALES[number];

export const DEFAULT_NAMESPACE = 'common';
