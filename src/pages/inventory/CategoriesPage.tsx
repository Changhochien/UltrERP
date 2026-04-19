import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { PageHeader, PageTabs, SectionCard } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { usePermissions } from "../../hooks/usePermissions";
import {
  createCategory,
  listCategories,
  setCategoryStatus,
  updateCategory,
} from "../../lib/api/inventory";
import type { Category } from "../../domain/inventory/types";
import { buildInventorySectionTabs, getInventorySectionRoute, type InventorySectionTabValue } from "./inventoryPageTabs";

function toFieldError(errors?: Array<{ field: string; message: string }>) {
  return errors?.find((error) => error.field === "name")?.message ?? null;
}

export function CategoriesPage() {
  const { t } = useTranslation("common", { keyPrefix: "inventory.categoriesPage" });
  const { t: tCommon } = useTranslation("common");
  const navigate = useNavigate();
  const { canWrite } = usePermissions();
  const inventoryTabs = buildInventorySectionTabs(tCommon);
  const [query, setQuery] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [items, setItems] = useState<Category[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const [editingCategoryId, setEditingCategoryId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [statusPendingId, setStatusPendingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    listCategories({
      q: query.trim() || undefined,
      activeOnly: !showInactive,
      limit: 100,
    })
      .then((response) => {
        if (!cancelled) {
          setItems(response.items);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setItems([]);
          setError(err instanceof Error ? err.message : t("loadError"));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [query, refreshKey, showInactive, t]);

  const isEditing = editingCategoryId !== null;
  const totalLabel = useMemo(() => t("categories", { count: items.length }), [items.length, t]);

  function resetForm() {
    setEditingCategoryId(null);
    setName("");
    setNameError(null);
    setFormError(null);
  }

  async function handleSaveCategory() {
    if (!name.trim()) {
      setNameError("Category name is required");
      return;
    }

    setSaving(true);
    setNameError(null);
    setFormError(null);

    const result = editingCategoryId
      ? await updateCategory(editingCategoryId, { name: name.trim() })
      : await createCategory({ name: name.trim() });

    setSaving(false);

    if (!result.ok) {
      setNameError(toFieldError(result.errors));
      setFormError(result.error);
      return;
    }

    resetForm();
    setRefreshKey((value) => value + 1);
  }

  async function handleToggleStatus(category: Category) {
    setStatusPendingId(category.id);
    setFormError(null);
    const result = await setCategoryStatus(category.id, category.is_active ? "inactive" : "active");
    setStatusPendingId(null);

    if (!result.ok) {
      setFormError(result.error || t("statusError"));
      return;
    }

    if (editingCategoryId === category.id && category.is_active) {
      resetForm();
    }

    setRefreshKey((value) => value + 1);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("title")}
        description={t("description")}
        tabs={(
          <PageTabs
            items={inventoryTabs}
            value="categories"
            ariaLabel={tCommon("inventory.page.title")}
            onValueChange={(next) => navigate(getInventorySectionRoute(next as InventorySectionTabValue))}
          />
        )}
      />

      {canWrite("inventory") ? (
        <SectionCard
          title={isEditing ? t("editTitle") : t("createTitle")}
          description={t("formDescription")}
        >
          <div className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="category-name" className="block text-sm font-medium">
                {t("nameLabel")}
              </label>
              <Input
                id="category-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder={t("namePlaceholder")}
                disabled={saving}
              />
              {nameError ? <p className="text-sm text-destructive">{nameError}</p> : null}
            </div>
            {formError ? <p className="text-sm text-destructive">{formError}</p> : null}
            <div className="flex flex-wrap gap-2">
              <Button type="button" onClick={handleSaveCategory} disabled={saving}>
                {saving ? t("saving") : isEditing ? t("update") : t("save")}
              </Button>
              {isEditing ? (
                <Button type="button" variant="outline" onClick={resetForm} disabled={saving}>
                  {t("cancelEdit")}
                </Button>
              ) : null}
            </div>
          </div>
        </SectionCard>
      ) : (
        <SectionCard title={t("createTitle")} description={t("readOnly")} />
      )}

      <SectionCard
        title={t("directoryTitle")}
        description={t("directoryDescription")}
        actions={<div className="text-sm text-muted-foreground">{totalLabel}</div>}
      >
        <div className="space-y-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="w-full max-w-md">
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={t("searchPlaceholder")}
                aria-label={t("searchPlaceholder")}
              />
            </div>
            <Button
              type="button"
              variant={showInactive ? "default" : "outline"}
              onClick={() => setShowInactive((value) => !value)}
              aria-pressed={showInactive}
            >
              {t("showInactive")}
            </Button>
          </div>

          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {formError && !canWrite("inventory") ? <p className="text-sm text-destructive">{formError}</p> : null}

          {loading ? (
            <p className="text-sm text-muted-foreground">{t("loading")}</p>
          ) : items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/80 px-4 py-8 text-center">
              <p className="font-medium">{t("empty")}</p>
              <p className="mt-1 text-sm text-muted-foreground">{t("emptyDescription")}</p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-border/70">
              <table className="min-w-full divide-y divide-border/70 text-sm">
                <thead className="bg-muted/30 text-left text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3 font-medium">{t("nameLabel")}</th>
                    <th className="px-4 py-3 font-medium">{t("status")}</th>
                    <th className="px-4 py-3 font-medium">{t("updated")}</th>
                    <th className="px-4 py-3 font-medium">{t("actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {items.map((category) => (
                    <tr key={category.id} className={!category.is_active ? "bg-muted/20 text-muted-foreground" : undefined}>
                      <td className="px-4 py-3 font-medium">{category.name}</td>
                      <td className="px-4 py-3">
                        <Badge variant={category.is_active ? "success" : "outline"} className="normal-case tracking-normal">
                          {category.is_active ? t("active") : t("inactive")}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">{category.updated_at.slice(0, 10)}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          {canWrite("inventory") ? (
                            <>
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setEditingCategoryId(category.id);
                                  setName(category.name);
                                  setNameError(null);
                                  setFormError(null);
                                }}
                              >
                                {t("edit")}
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant={category.is_active ? "outline" : "default"}
                                onClick={() => handleToggleStatus(category)}
                                disabled={statusPendingId === category.id}
                              >
                                {category.is_active ? t("deactivate") : t("activate")}
                              </Button>
                            </>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
