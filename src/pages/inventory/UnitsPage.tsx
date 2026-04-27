import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { PageHeader, PageTabs, SectionCard } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { usePermissions } from "../../hooks/usePermissions";
import {
  createUnit,
  listUnits,
  setUnitStatus,
  updateUnit,
} from "../../lib/api/inventory";
import type { UnitOfMeasure } from "../../domain/inventory/types";
import { buildInventorySectionTabs, getInventorySectionRoute, type InventorySectionTabValue } from "./inventoryPageTabs";

function toFieldError(field: string, errors?: Array<{ field: string; message: string }>) {
  return errors?.find((error) => error.field === field)?.message ?? null;
}

export function UnitsPage() {
  const { t } = useTranslation("inventory");
  const { t: tRoutes } = useTranslation("routes");
  const navigate = useNavigate();
  const { canWrite } = usePermissions();
  const inventoryTabs = buildInventorySectionTabs(tRoutes);
  const [query, setQuery] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [items, setItems] = useState<UnitOfMeasure[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const [editingUnitId, setEditingUnitId] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [decimalPlaces, setDecimalPlaces] = useState("0");
  const [codeError, setCodeError] = useState<string | null>(null);
  const [nameError, setNameError] = useState<string | null>(null);
  const [decimalPlacesError, setDecimalPlacesError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [statusPendingId, setStatusPendingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    listUnits({
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
          setError(err instanceof Error ? err.message : t("unitsPage.loadError"));
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

  const isEditing = editingUnitId !== null;
  const totalLabel = useMemo(() => t("units", { count: items.length }), [items.length, t]);

  function resetForm() {
    setEditingUnitId(null);
    setCode("");
    setName("");
    setDecimalPlaces("0");
    setCodeError(null);
    setNameError(null);
    setDecimalPlacesError(null);
    setFormError(null);
  }

  function validateForm() {
    let valid = true;
    setCodeError(null);
    setNameError(null);
    setDecimalPlacesError(null);

    if (!code.trim()) {
      setCodeError(t("unitsPage.codeRequired"));
      valid = false;
    }
    if (!name.trim()) {
      setNameError(t("unitsPage.nameRequired"));
      valid = false;
    }
    const parsedDecimalPlaces = Number(decimalPlaces);
    if (!Number.isInteger(parsedDecimalPlaces) || parsedDecimalPlaces < 0 || parsedDecimalPlaces > 6) {
      setDecimalPlacesError(t("unitsPage.decimalPlacesInvalid"));
      valid = false;
    }

    return valid;
  }

  async function handleSaveUnit() {
    if (!validateForm()) {
      return;
    }

    setSaving(true);
    setFormError(null);

    const payload = {
      code: code.trim(),
      name: name.trim(),
      decimal_places: Number(decimalPlaces),
    };
    const result = editingUnitId
      ? await updateUnit(editingUnitId, payload)
      : await createUnit(payload);

    setSaving(false);

    if (!result.ok) {
      setCodeError(toFieldError("code", result.errors));
      setNameError(toFieldError("name", result.errors));
      setDecimalPlacesError(toFieldError("decimal_places", result.errors));
      setFormError(result.error);
      return;
    }

    resetForm();
    setRefreshKey((value) => value + 1);
  }

  async function handleToggleStatus(unit: UnitOfMeasure) {
    setStatusPendingId(unit.id);
    setFormError(null);
    const result = await setUnitStatus(unit.id, !unit.is_active);
    setStatusPendingId(null);

    if (!result.ok) {
      setFormError(result.error || t("unitsPage.statusError"));
      return;
    }

    if (editingUnitId === unit.id && unit.is_active) {
      resetForm();
    }

    setRefreshKey((value) => value + 1);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: tRoutes("inventoryUnits.label") }]}
        eyebrow={t("unitsPage.eyebrow")}
        title={t("unitsPage.title")}
        description={t("unitsPage.description")}
        tabs={(
          <PageTabs
            items={inventoryTabs}
            value="units"
            ariaLabel={t("page.title")}
            onValueChange={(next) => navigate(getInventorySectionRoute(next as InventorySectionTabValue))}
          />
        )}
      />

      {canWrite("inventory") ? (
        <SectionCard
          title={isEditing ? t("unitsPage.editTitle") : t("unitsPage.createTitle")}
          description={t("unitsPage.formDescription")}
        >
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label htmlFor="unit-code" className="block text-sm font-medium">
                  {t("unitsPage.codeLabel")}
                </label>
                <Input
                  id="unit-code"
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  placeholder={t("unitsPage.codePlaceholder")}
                  disabled={saving}
                />
                {codeError ? <p className="text-sm text-destructive">{codeError}</p> : null}
              </div>
              <div className="space-y-2">
                <label htmlFor="unit-name" className="block text-sm font-medium">
                  {t("unitsPage.nameLabel")}
                </label>
                <Input
                  id="unit-name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder={t("unitsPage.namePlaceholder")}
                  disabled={saving}
                />
                {nameError ? <p className="text-sm text-destructive">{nameError}</p> : null}
              </div>
            </div>

            <div className="space-y-2">
              <label htmlFor="unit-decimal-places" className="block text-sm font-medium">
                {t("unitsPage.decimalPlacesLabel")}
              </label>
              <Input
                id="unit-decimal-places"
                type="number"
                min={0}
                max={6}
                step={1}
                value={decimalPlaces}
                onChange={(event) => setDecimalPlaces(event.target.value)}
                disabled={saving}
              />
              {decimalPlacesError ? <p className="text-sm text-destructive">{decimalPlacesError}</p> : null}
            </div>

            {formError ? <p className="text-sm text-destructive">{formError}</p> : null}
            <div className="flex flex-wrap gap-2">
              <Button type="button" onClick={handleSaveUnit} disabled={saving}>
                {saving ? t("unitsPage.saving") : isEditing ? t("unitsPage.update") : t("unitsPage.save")}
              </Button>
              {isEditing ? (
                <Button type="button" variant="outline" onClick={resetForm} disabled={saving}>
                  {t("unitsPage.cancelEdit")}
                </Button>
              ) : null}
            </div>
          </div>
        </SectionCard>
      ) : (
        <SectionCard title={t("unitsPage.createTitle")} description={t("unitsPage.readOnly")} />
      )}

      <SectionCard
        title={t("unitsPage.directoryTitle")}
        description={t("unitsPage.directoryDescription")}
        actions={<div className="text-sm text-muted-foreground">{totalLabel}</div>}
      >
        <div className="space-y-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="w-full max-w-md">
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={t("unitsPage.searchPlaceholder")}
                aria-label={t("unitsPage.searchPlaceholder")}
              />
            </div>
            <Button
              type="button"
              variant={showInactive ? "default" : "outline"}
              onClick={() => setShowInactive((value) => !value)}
              aria-pressed={showInactive}
            >
              {t("unitsPage.showInactive")}
            </Button>
          </div>

          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {formError && !canWrite("inventory") ? <p className="text-sm text-destructive">{formError}</p> : null}

          {loading ? (
            <p className="text-sm text-muted-foreground">{t("unitsPage.loading")}</p>
          ) : items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/80 px-4 py-8 text-center">
              <p className="font-medium">{t("unitsPage.empty")}</p>
              <p className="mt-1 text-sm text-muted-foreground">{t("unitsPage.emptyDescription")}</p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-border/70">
              <table className="min-w-full divide-y divide-border/70 text-sm">
                <thead className="bg-muted/30 text-left text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3 font-medium">{t("unitsPage.codeLabel")}</th>
                    <th className="px-4 py-3 font-medium">{t("unitsPage.nameLabel")}</th>
                    <th className="px-4 py-3 font-medium">{t("unitsPage.decimalPlacesLabel")}</th>
                    <th className="px-4 py-3 font-medium">{t("unitsPage.status")}</th>
                    <th className="px-4 py-3 font-medium">{t("unitsPage.updated")}</th>
                    <th className="px-4 py-3 font-medium">{t("unitsPage.actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {items.map((unit) => (
                    <tr key={unit.id} className={!unit.is_active ? "bg-muted/20 text-muted-foreground" : undefined}>
                      <td className="px-4 py-3 font-medium">{unit.code}</td>
                      <td className="px-4 py-3">{unit.name}</td>
                      <td className="px-4 py-3">{unit.decimal_places}</td>
                      <td className="px-4 py-3">
                        <Badge variant={unit.is_active ? "success" : "outline"} className="normal-case tracking-normal">
                          {unit.is_active ? t("unitsPage.active") : t("unitsPage.inactive")}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">{unit.updated_at.slice(0, 10)}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          {canWrite("inventory") ? (
                            <>
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setEditingUnitId(unit.id);
                                  setCode(unit.code);
                                  setName(unit.name);
                                  setDecimalPlaces(String(unit.decimal_places));
                                  setCodeError(null);
                                  setNameError(null);
                                  setDecimalPlacesError(null);
                                  setFormError(null);
                                }}
                              >
                                {t("unitsPage.edit")}
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant={unit.is_active ? "outline" : "default"}
                                onClick={() => handleToggleStatus(unit)}
                                disabled={statusPendingId === unit.id}
                              >
                                {unit.is_active ? t("unitsPage.deactivate") : t("unitsPage.activate")}
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
