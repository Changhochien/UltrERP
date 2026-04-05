import { beforeAll } from "vitest";
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import enTranslations from "../../../public/locales/en/common.json";

beforeAll(async () => {
  if (!i18n.isInitialized) {
    await i18n
      .use(initReactI18next)
      .init({
        lng: "en",
        fallbackLng: "en",
        resources: {
          en: { common: enTranslations },
        },
        interpolation: {
          escapeValue: false,
          prefix: "{",
          suffix: "}",
        },
        ns: ["common"],
        defaultNS: "common",
        backend: {
          loadPath: "/locales/{lng}/{ns}.json",
        },
      });
  } else {
    i18n.addResourceBundle("en", "common", enTranslations, true, true);
    await i18n.changeLanguage("en");
    // Ensure interpolation prefix/suffix are set correctly for test environment
    if (i18n.options.interpolation) {
      i18n.options.interpolation.prefix = "{";
      i18n.options.interpolation.suffix = "}";
    }
  }
});
