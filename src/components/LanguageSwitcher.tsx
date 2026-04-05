import { Check, Globe } from "lucide-react";
import { useTranslation } from "react-i18next";

const LANGUAGE_OPTIONS = [
  { value: "en", labelKey: "languageSwitcher.english", nativeLabel: "English" },
  { value: "zh-Hant", labelKey: "languageSwitcher.traditionalChinese", nativeLabel: "繁體中文" },
] as const;

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation("common");
  const currentLanguage = i18n.resolvedLanguage ?? i18n.language;
  const currentOption = LANGUAGE_OPTIONS.find((option) => option.value === currentLanguage);

  return (
    <div
      role="group"
      aria-label={t("languageSwitcher.currentSelection", {
        language: currentOption ? t(currentOption.labelKey) : currentLanguage,
      })}
      className="flex w-full flex-wrap items-center gap-1 rounded-full border border-border/80 bg-card/80 p-1 shadow-sm"
    >
      {LANGUAGE_OPTIONS.map((option) => {
        const isActive = currentLanguage === option.value;
        const optionLabel = t(option.labelKey);

        return (
          <button
            key={option.value}
            type="button"
            className={[
              "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-sm font-medium transition-colors",
              isActive
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            ].join(" ")}
            onClick={() => void i18n.changeLanguage(option.value)}
            aria-pressed={isActive}
            aria-label={t("languageSwitcher.useLanguage", { language: optionLabel })}
            title={`${option.nativeLabel} (${optionLabel})`}
          >
            <Globe className="size-3.5" />
            <span className="text-xs">{option.nativeLabel}</span>
            {isActive && <Check className="size-3" />}
          </button>
        );
      })}
    </div>
  );
}
