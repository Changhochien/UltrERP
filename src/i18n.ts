import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import HttpBackend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';

const TRADITIONAL_CHINESE_LOCALES = new Set(['zh-TW', 'zh-Hant', 'zh-HK']);
const SIMPLIFIED_CHINESE_LOCALES = new Set(['zh-CN', 'zh-SG', 'zh-MO']);

export function mapDetectedLanguage(language?: string) {
  if (!language) {
    return 'en';
  }

  if (TRADITIONAL_CHINESE_LOCALES.has(language)) {
    return 'zh-Hant';
  }

  if (SIMPLIFIED_CHINESE_LOCALES.has(language)) {
    return 'en';
  }

  if (language.startsWith('en')) {
    return 'en';
  }

  return language === 'zh-Hant' ? 'zh-Hant' : 'en';
}

function syncDocumentLanguage(language?: string) {
  if (typeof document === 'undefined') {
    return;
  }

  document.documentElement.lang = language === 'zh-Hant' ? 'zh-Hant' : 'en';
}

i18n.on('languageChanged', syncDocumentLanguage);

void i18n
  .use(HttpBackend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    supportedLngs: ['en', 'zh-Hant'],
    fallbackLng: 'en',
    defaultNS: 'common',
    ns: ['common'],
    backend: {
      loadPath: '/locales/{lng}/{ns}.json',
    },
    detection: {
      order: ['localStorage', 'navigator', 'querystring'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
      convertDetectedLanguage: mapDetectedLanguage,
    },
    interpolation: {
      escapeValue: false,
      prefix: '{',
      suffix: '}',
    },
  })
  .then(() => {
    syncDocumentLanguage(i18n.resolvedLanguage ?? i18n.language);
  });

export default i18n;
