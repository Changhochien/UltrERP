import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Settings } from "lucide-react";

import { PageHeader, PageTabs, SectionCard, SurfaceMessage } from "../../components/layout/PageLayout";
import { Skeleton } from "../../components/ui/skeleton";
import { SettingField } from "../../components/settings/SettingField";
import {
  useSettings,
  useUpdateSetting,
  useResetSetting,
} from "../../hooks/useSettings";
import type { SettingsCategory } from "../../lib/api/settings";

interface CategoryInfo {
  label: string;
  description: string;
}

function getCategoryInfo(category: string, t: (key: string, options?: Record<string, unknown>) => string): CategoryInfo {
  const key = `settingsPage.categories.${category}`;
  const label = t(`${key}.label`, { defaultValue: category.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()) });
  const description = t(`${key}.description`, { defaultValue: '' });
  return { label, description };
}

function SettingsLoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex gap-2">
        <Skeleton className="h-10 w-32 rounded-[1.1rem]" />
        <Skeleton className="h-10 w-28 rounded-[1.1rem]" />
        <Skeleton className="h-10 w-24 rounded-[1.1rem]" />
      </div>
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-28 w-full rounded-2xl" />
        ))}
      </div>
    </div>
  );
}

function CategoryContent({
  category,
  categoryInfo,
  onSave,
  onReset,
  savingKey,
  resettingKey,
  errorKey,
  saveError,
}: {
  category: SettingsCategory;
  categoryInfo: CategoryInfo;
  onSave: (key: string, value: string, valueType: string) => Promise<void>;
  onReset: (key: string) => Promise<void>;
  savingKey: string | null;
  resettingKey: string | null;
  errorKey: string | null;
  saveError: string | null;
}) {
  const { t } = useTranslation("common");

  if (category.items.length === 0) {
    return (
      <SectionCard>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="mb-4 rounded-full bg-muted/50 p-4">
            <Settings className="size-8 text-muted-foreground/50" />
          </div>
          <p className="text-sm font-medium text-muted-foreground">
            {t("settingsPage.emptyCategory")}
          </p>
          <p className="mt-1 text-xs text-muted-foreground/60">
            {t("settingsPage.configureMessage")}
          </p>
        </div>
      </SectionCard>
    );
  }

  return (
    <SectionCard
      title={categoryInfo.label}
      description={categoryInfo.description || category.description}
      actions={
        <span className="text-xs text-muted-foreground">
          {category.items.length} {category.items.length === 1 ? t("settingsPage.settingsCount_one", { count: 1 }) : t("settingsPage.settingsCount_other", { count: category.items.length })}
        </span>
      }
    >
      <div className="space-y-4">
        {category.items.map((item) => (
          <SettingField
            key={item.key}
            item={item}
            onSave={onSave}
            onReset={onReset}
            saving={savingKey === item.key}
            resetting={resettingKey === item.key}
            error={errorKey === item.key ? saveError : null}
          />
        ))}
      </div>
    </SectionCard>
  );
}

export function SettingsPage() {
  const { t } = useTranslation("common");
  const { categories, loading, error, refresh } = useSettings();
  const { updateSetting } = useUpdateSetting();
  const { resetSetting } = useResetSetting();
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [resettingKey, setResettingKey] = useState<string | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [lastReset, setLastReset] = useState<{ key: string; value: string } | null>(null);

  // Set first category as active once loaded
  const currentCategory = activeCategory ?? (categories[0]?.category ?? null);

  // Build page tab items from categories
  const pageTabItems = categories.map((cat) => {
    const info = getCategoryInfo(cat.category, t);
    return {
      value: cat.category,
      label: info.label,
    };
  });

  // Find current category data
  const currentCategoryData = categories.find((c) => c.category === currentCategory) ?? null;

  async function handleSave(key: string, value: string, valueType: string) {
    setSaveError(null);
    setErrorKey(null);

    // Client-side validation
    if (valueType === "int") {
      const num = Number(value);
      if (isNaN(num) || !Number.isInteger(num)) {
        const msg = t("settingsPage.invalidInt");
        setSaveError(msg);
        setErrorKey(key);
        return;
      }
    }
    if (valueType === "json" || valueType === "tuple") {
      try {
        JSON.parse(value);
      } catch {
        const msg = t("settingsPage.invalidJson");
        setSaveError(msg);
        setErrorKey(key);
        return;
      }
    }

    setSavingKey(key);
    try {
      await updateSetting(key, value);
      await refresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : t("settingsPage.saveError");
      setSaveError(msg);
      setErrorKey(key);
    } finally {
      setSavingKey(null);
    }
  }

  async function handleReset(key: string) {
    setResetError(null);
    setResettingKey(key);
    // Capture current value so user can undo
    const item = categories.flatMap((c) => c.items).find((i) => i.key === key);
    if (item && !item.is_null) {
      setLastReset({ key, value: item.value });
    }
    try {
      await resetSetting(key);
      await refresh();
      // Clear undo state after 5s
      setTimeout(() => setLastReset(null), 5000);
    } catch (err) {
      setResetError(err instanceof Error ? err.message : t("settingsPage.resetError"));
      setLastReset(null);
    } finally {
      setResettingKey(null);
    }
  }

  async function handleUndoReset() {
    if (!lastReset) return;
    setSaveError(null);
    setSavingKey(lastReset.key);
    try {
      await updateSetting(lastReset.key, lastReset.value);
      await refresh();
      setLastReset(null);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : t("settingsPage.saveError"));
    } finally {
      setSavingKey(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow={t("settingsPage.eyebrow")}
          title={t("settingsPage.title")}
          description={t("settingsPage.description")}
        />
        <SettingsLoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow={t("settingsPage.eyebrow")}
          title={t("settingsPage.title")}
          description={t("settingsPage.description")}
        />
        <SurfaceMessage tone="danger">{error}</SurfaceMessage>
      </div>
    );
  }

  if (categories.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow={t("settingsPage.eyebrow")}
          title={t("settingsPage.title")}
          description={t("settingsPage.description")}
        />
        <SurfaceMessage tone="default">
          {t("settingsPage.noCategories")}
        </SurfaceMessage>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("settingsPage.eyebrow")}
        title={t("settingsPage.title")}
        description={t("settingsPage.description")}
        tabs={
          <PageTabs
            items={pageTabItems}
            value={currentCategory ?? ""}
            onValueChange={setActiveCategory}
            ariaLabel={t("settingsPage.title")}
          />
        }
      />

      {(saveError || resetError) ? (
        <SurfaceMessage tone="danger">
          {saveError || resetError}
        </SurfaceMessage>
      ) : null}

      {lastReset ? (
        <SurfaceMessage tone="default">
          {t("settingsPage.resetDone")}{" "}
          <button
            type="button"
            className="underline underline-offset-2 font-medium"
            onClick={handleUndoReset}
          >
            {t("settingsPage.undo")}
          </button>
        </SurfaceMessage>
      ) : null}

      {currentCategoryData && (
        <CategoryContent
          category={currentCategoryData}
          categoryInfo={getCategoryInfo(currentCategoryData.category, t)}
          onSave={handleSave}
          onReset={handleReset}
          savingKey={savingKey}
          resettingKey={resettingKey}
          errorKey={errorKey}
          saveError={saveError}
        />
      )}
    </div>
  );
}

export default SettingsPage;
