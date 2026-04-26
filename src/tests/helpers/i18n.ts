import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { I18N_NAMESPACES, DEFAULT_NAMESPACE } from '../../lib/i18n-namespaces';

// English translations - imported dynamically by namespace
import enCommon from '../../../public/locales/en/common.json';
import enShell from '../../../public/locales/en/shell.json';
import enRoutes from '../../../public/locales/en/routes.json';
import enAuth from '../../../public/locales/en/auth.json';
import enDashboard from '../../../public/locales/en/dashboard.json';
import enAdmin from '../../../public/locales/en/admin.json';
import enIntelligence from '../../../public/locales/en/intelligence.json';
import enCrm from '../../../public/locales/en/crm.json';
import enCustomer from '../../../public/locales/en/customer.json';
import enInventory from '../../../public/locales/en/inventory.json';
import enOrders from '../../../public/locales/en/orders.json';
import enProcurement from '../../../public/locales/en/procurement.json';
import enPurchase from '../../../public/locales/en/purchase.json';
import enInvoice from '../../../public/locales/en/invoice.json';
import enPayments from '../../../public/locales/en/payments.json';
import enSettings from '../../../public/locales/en/settings.json';

const enTranslations: Record<string, Record<string, unknown>> = {
  common: enCommon,
  shell: enShell,
  routes: enRoutes,
  auth: enAuth,
  dashboard: enDashboard,
  admin: enAdmin,
  intelligence: enIntelligence,
  crm: enCrm,
  customer: enCustomer,
  inventory: enInventory,
  orders: enOrders,
  procurement: enProcurement,
  purchase: enPurchase,
  invoice: enInvoice,
  payments: enPayments,
  settings: enSettings,
};

const initOptions = {
  lng: 'en',
  fallbackLng: 'en',
  resources: { en: enTranslations },
  interpolation: { escapeValue: false, prefix: '{', suffix: '}' },
  ns: I18N_NAMESPACES,
  defaultNS: DEFAULT_NAMESPACE,
  backend: { loadPath: '/locales/{lng}/{ns}.json' },
};

if (!i18n.isInitialized) {
  void i18n.use(initReactI18next).init(initOptions);
} else {
  // Add missing resource bundles to existing instance
  for (const ns of I18N_NAMESPACES) {
    if (!i18n.getResourceBundle('en', ns)) {
      i18n.addResourceBundle('en', ns, enTranslations[ns], true, true);
    }
  }
  void i18n.changeLanguage('en');

  // Sync options
  if (i18n.options) {
    i18n.options.ns = I18N_NAMESPACES;
    i18n.options.defaultNS = DEFAULT_NAMESPACE;
    i18n.options.interpolation = { prefix: '{', suffix: '}' };
  }
}
