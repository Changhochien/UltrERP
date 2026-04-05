import { useState } from "react";
import { useTranslation } from "react-i18next";

import { PageHeader, SectionCard, SurfaceMessage } from "../../components/layout/PageLayout";
import { Skeleton } from "../../components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { SettingField } from "../../components/settings/SettingField";
import {
  useSettings,
  useUpdateSetting,
  useResetSetting,
} from "../../hooks/useSettings";
import type { SettingsCategory } from "../../lib/api/settings";

function SettingsLoadingSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-40 w-full" />
      <div className="space-y-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    </div>
  );
}

function CategoryContent({
  category,
  onSave,
  onReset,
  savingKey,
  resettingKey,
}: {
  category: SettingsCategory;
  onSave: (key: string, value: string) => Promise<void>;
  onReset: (key: string) => Promise<void>;
  savingKey: string | null;
  resettingKey: string | null;
}) {
  const { t } = useTranslation("common");

  if (category.items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        {t("settingsPage.emptyCategory", "No settings in this category.")}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {category.items.map((item) => (
        <SectionCard key={item.key}>
          <SettingField
            item={item}
            onSave={onSave}
            onReset={onReset}
            saving={savingKey === item.key}
            resetting={resettingKey === item.key}
          />
        </SectionCard>
      ))}
    </div>
  );
}

export function SettingsPage() {
  const { t } = useTranslation("common");
  const { categories, loading, error, refresh } = useSettings();
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [resettingKey, setResettingKey] = useState<string | null>(null);

  // Set first category as active once loaded
  const currentCategory = activeCategory ?? (categories[0]?.category ?? null);

  async function handleSave(key: string, value: string) {
    setSaveError(null);
    setSavingKey(key);
    try {
      const { updateSetting: update } = useUpdateSetting();
      await update(key, value);
      await refresh();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : t("settingsPage.saveError", "Failed to save setting."));
    } finally {
      setSavingKey(null);
    }
  }

  async function handleReset(key: string) {
    setResetError(null);
    setResettingKey(key);
    try {
      const { resetSetting: reset } = useResetSetting();
      await reset(key);
      await refresh();
    } catch (err) {
      setResetError(err instanceof Error ? err.message : t("settingsPage.resetError", "Failed to reset setting."));
    } finally {
      setResettingKey(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow={t("settingsPage.eyebrow", "Configuration")}
          title={t("routes.settings.label", "Settings")}
          description={t("routes.settings.description", "Manage workspace settings and preferences.")}
        />
        <SettingsLoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow={t("settingsPage.eyebrow", "Configuration")}
          title={t("routes.settings.label", "Settings")}
          description={t("routes.settings.description", "Manage workspace settings and preferences.")}
        />
        <SurfaceMessage tone="danger">{error}</SurfaceMessage>
      </div>
    );
  }

  if (categories.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow={t("settingsPage.eyebrow", "Configuration")}
          title={t("routes.settings.label", "Settings")}
          description={t("routes.settings.description", "Manage workspace settings and preferences.")}
        />
        <SurfaceMessage tone="default">
          {t("settingsPage.noCategories", "No settings categories available.")}
        </SurfaceMessage>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("settingsPage.eyebrow", "Configuration")}
        title={t("routes.settings.label", "Settings")}
        description={t(
          "routes.settings.description",
          "Manage workspace settings and preferences.",
        )}
      />

      {(saveError || resetError) ? (
        <SurfaceMessage tone="danger">
          {saveError || resetError}
        </SurfaceMessage>
      ) : null}

      <Tabs
        value={currentCategory ?? undefined}
        onValueChange={setActiveCategory}
      >
        <TabsList className="w-full flex-wrap h-auto gap-1">
          {categories.map((cat) => (
            <TabsTrigger key={cat.category} value={cat.category}>
              {cat.category}
            </TabsTrigger>
          ))}
        </TabsList>

        {categories.map((cat) => (
          <TabsContent key={cat.category} value={cat.category} className="mt-6 space-y-4">
            <CategoryContent
              category={cat}
              onSave={handleSave}
              onReset={handleReset}
              savingKey={savingKey}
              resettingKey={resettingKey}
            />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

export default SettingsPage;
