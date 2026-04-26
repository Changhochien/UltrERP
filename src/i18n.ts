import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import HttpBackend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';
import { I18N_NAMESPACES, SUPPORTED_LOCALES, DEFAULT_NAMESPACE } from './lib/i18n-namespaces';

const TRADITIONAL_CHINESE = ['zh-TW', 'zh-Hant', 'zh-HK'];
const SIMPLIFIED_CHINESE = ['zh-CN', 'zh-SG', 'zh-MO'];

function mapDetectedLanguage(language: string | undefined): 'en' | 'zh-Hant' {
  if (!language) return 'en';
  if (TRADITIONAL_CHINESE.includes(language)) return 'zh-Hant';
  if (SIMPLIFIED_CHINESE.includes(language)) return 'en';
  if (language.startsWith('en') || language === 'zh-Hant') return 'en';
  return 'en';
}

function syncDocumentLanguage(language: string | undefined) {
  if (typeof document === 'undefined') return;
  document.documentElement.lang = language === 'zh-Hant' ? 'zh-Hant' : 'en';
}

i18n.on('languageChanged', syncDocumentLanguage);

void i18n
  .use(HttpBackend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    supportedLngs: SUPPORTED_LOCALES,
    fallbackLng: 'en',
    defaultNS: DEFAULT_NAMESPACE,
    ns: I18N_NAMESPACES,
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
