import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";
import {
  Settings,
  ShieldCheck,
  Bell,
  Key,
  Globe,
  Database,
  Palette,
} from "lucide-react";

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

function toTitleCase(str: string): string {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function getCategoryIcon(category: string): ReactNode {
  const iconMap: Record<string, ReactNode> = {
    general: <Globe className="size-4" />,
    notification: <Bell className="size-4" />,
    notifications: <Bell className="size-4" />,
    security: <ShieldCheck className="size-4" />,
    appearance: <Palette className="size-4" />,
    data: <Database className="size-4" />,
    api: <Key className="size-4" />,
    privacy: <Key className="size-4" />,
  };
  return iconMap[category.toLowerCase()] ?? <Settings className="size-4" />;
}

function SettingsLoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex gap-2">
        <Skeleton className="h-9 w-24 rounded-lg" />
        <Skeleton className="h-9 w-24 rounded-lg" />
        <Skeleton className="h-9 w-24 rounded-lg" />
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
  onSave,
  onReset,
  savingKey,
  resettingKey,
  errorKey,
  saveError,
}: {
  category: SettingsCategory;
  onSave: (key: string, value: string) => Promise<void>;
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
        <p className="py-6 text-center text-sm text-muted-foreground">
          {t("settingsPage.emptyCategory", "No settings in this category.")}
        </p>
      </SectionCard>
    );
  }

  return (
    <SectionCard>
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

  // Set first category as active once loaded
  const currentCategory = activeCategory ?? (categories[0]?.category ?? null);

  async function handleSave(key: string, value: string) {
    setSaveError(null);
    setErrorKey(null);
    setSavingKey(key);
    try {
      await updateSetting(key, value);
      await refresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : t("settingsPage.saveError", "Failed to save setting.");
      setSaveError(msg);
      setErrorKey(key);
    } finally {
      setSavingKey(null);
    }
  }

  async function handleReset(key: string) {
    setResetError(null);
    setResettingKey(key);
    try {
      await resetSetting(key);
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
        <TabsList className="inline-flex items-center rounded-xl bg-muted/60 p-1 gap-1 overflow-x-auto">
          {categories.map((cat) => (
            <TabsTrigger key={cat.category} value={cat.category} className="gap-1.5 shrink-0">
              {getCategoryIcon(cat.category)}
              <span className="truncate max-w-24">{toTitleCase(cat.category)}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        {categories.map((cat) => (
          <TabsContent key={cat.category} value={cat.category} className="mt-6">
            <CategoryContent
              category={cat}
              onSave={handleSave}
              onReset={handleReset}
              savingKey={savingKey}
              resettingKey={resettingKey}
              errorKey={errorKey}
              saveError={saveError}
            />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

export default SettingsPage;
