import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { SectionCard, SurfaceMessage } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createProductSupplier,
  deleteProductSupplier,
  listProductSuppliers,
  updateProductSupplier,
} from "@/lib/api/inventory";
import { useSuppliers } from "../hooks/useSuppliers";
import type { ProductSupplierAssociation } from "../types";

interface ProductSuppliersPanelProps {
  productId: string;
}

interface SupplierDraft {
  unitCost: string;
  leadTimeDays: string;
}

function toDraft(association: ProductSupplierAssociation): SupplierDraft {
  return {
    unitCost: association.unit_cost?.toString() ?? "",
    leadTimeDays: association.lead_time_days?.toString() ?? "",
  };
}

function parseOptionalNumber(value: string): number | undefined {
  const normalized = value.trim();
  if (!normalized) {
    return undefined;
  }

  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function parseOptionalInteger(value: string): number | undefined {
  const parsed = parseOptionalNumber(value);
  if (parsed == null) {
    return undefined;
  }
  return Math.trunc(parsed);
}

export function ProductSuppliersPanel({ productId }: ProductSuppliersPanelProps) {
  const { t } = useTranslation("common", { keyPrefix: "inventory.productDetail.suppliersPanel" });
  const { suppliers, loading: suppliersLoading } = useSuppliers({ activeOnly: true });

  const [associations, setAssociations] = useState<ProductSupplierAssociation[]>([]);
  const [drafts, setDrafts] = useState<Record<string, SupplierDraft>>({});
  const [selectedSupplierId, setSelectedSupplierId] = useState("");
  const [newUnitCost, setNewUnitCost] = useState("");
  const [newLeadTimeDays, setNewLeadTimeDays] = useState("");
  const [newIsDefault, setNewIsDefault] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const availableSuppliers = useMemo(
    () => suppliers.filter((supplier) => !associations.some((item) => item.supplier_id === supplier.id)),
    [associations, suppliers],
  );

  const loadAssociations = async () => {
    setLoading(true);
    setError(null);
    const response = await listProductSuppliers(productId);
    if (response.ok) {
      setAssociations(response.data.items);
      setDrafts(
        Object.fromEntries(response.data.items.map((item) => [item.supplier_id, toDraft(item)])),
      );
    } else {
      setAssociations([]);
      setDrafts({});
      setError(response.error);
    }
    setLoading(false);
  };

  useEffect(() => {
    let cancelled = false;

    async function runLoad() {
      setLoading(true);
      setError(null);
      const response = await listProductSuppliers(productId);
      if (cancelled) {
        return;
      }

      if (response.ok) {
        setAssociations(response.data.items);
        setDrafts(
          Object.fromEntries(response.data.items.map((item) => [item.supplier_id, toDraft(item)])),
        );
      } else {
        setAssociations([]);
        setDrafts({});
        setError(response.error);
      }
      setLoading(false);
    }

    void runLoad();
    return () => {
      cancelled = true;
    };
  }, [productId]);

  const handleDraftChange = (
    supplierId: string,
    field: keyof SupplierDraft,
    value: string,
  ) => {
    setDrafts((current) => ({
      ...current,
      [supplierId]: {
        ...(current[supplierId] ?? { unitCost: "", leadTimeDays: "" }),
        [field]: value,
      },
    }));
  };

  const handleAdd = async () => {
    if (!selectedSupplierId) {
      return;
    }

    setSaving(true);
    setError(null);
    const response = await createProductSupplier(productId, {
      supplier_id: selectedSupplierId,
      unit_cost: parseOptionalNumber(newUnitCost),
      lead_time_days: parseOptionalInteger(newLeadTimeDays),
      is_default: newIsDefault,
    });
    if (!response.ok) {
      setError(response.error);
      setSaving(false);
      return;
    }

    setSelectedSupplierId("");
    setNewUnitCost("");
    setNewLeadTimeDays("");
    setNewIsDefault(false);
    await loadAssociations();
    setSaving(false);
  };

  const handleSave = async (association: ProductSupplierAssociation) => {
    const draft = drafts[association.supplier_id] ?? toDraft(association);
    setSaving(true);
    setError(null);
    const response = await updateProductSupplier(productId, association.supplier_id, {
      unit_cost: parseOptionalNumber(draft.unitCost),
      lead_time_days: parseOptionalInteger(draft.leadTimeDays),
    });
    if (!response.ok) {
      setError(response.error);
      setSaving(false);
      return;
    }

    await loadAssociations();
    setSaving(false);
  };

  const handleMakeDefault = async (supplierId: string) => {
    setSaving(true);
    setError(null);
    const response = await updateProductSupplier(productId, supplierId, { is_default: true });
    if (!response.ok) {
      setError(response.error);
      setSaving(false);
      return;
    }

    await loadAssociations();
    setSaving(false);
  };

  const handleRemove = async (supplierId: string) => {
    setSaving(true);
    setError(null);
    const response = await deleteProductSupplier(productId, supplierId);
    if (!response.ok) {
      setError(response.error);
      setSaving(false);
      return;
    }

    await loadAssociations();
    setSaving(false);
  };

  return (
    <SectionCard title={t("title")} description={t("description")}>
      <div className="space-y-4">
        {error ? <SurfaceMessage tone="danger">{error}</SurfaceMessage> : null}

        <div className="grid gap-3 rounded-xl border border-border/70 bg-muted/20 p-4 md:grid-cols-[minmax(0,2fr)_1fr_1fr_auto_auto]">
          <label className="space-y-2 text-sm">
            <span>{t("supplier")}</span>
            <select
              value={selectedSupplierId}
              onChange={(event) => setSelectedSupplierId(event.target.value)}
              className="h-10 rounded-lg border border-input bg-background px-3"
              aria-label={t("supplier")}
            >
              <option value="">{t("selectSupplier")}</option>
              {availableSuppliers.map((supplier) => (
                <option key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-2 text-sm">
            <span>{t("unitCost")}</span>
            <Input
              value={newUnitCost}
              onChange={(event) => setNewUnitCost(event.target.value)}
              aria-label={t("unitCost")}
            />
          </label>

          <label className="space-y-2 text-sm">
            <span>{t("leadTimeDays")}</span>
            <Input
              value={newLeadTimeDays}
              onChange={(event) => setNewLeadTimeDays(event.target.value)}
              aria-label={t("leadTimeDays")}
            />
          </label>

          <label className="flex items-center gap-2 self-end pb-2 text-sm">
            <input
              type="checkbox"
              checked={newIsDefault}
              onChange={(event) => setNewIsDefault(event.target.checked)}
              aria-label={t("defaultSupplier")}
            />
            <span>{t("defaultSupplier")}</span>
          </label>

          <Button type="button" onClick={() => void handleAdd()} disabled={!selectedSupplierId || saving}>
            {saving ? t("saving") : t("add")}
          </Button>
        </div>

        {loading || suppliersLoading ? <p aria-busy="true">{t("loading")}</p> : null}

        {!loading && !suppliersLoading && associations.length === 0 ? (
          <SurfaceMessage>{t("empty")}</SurfaceMessage>
        ) : null}

        {associations.length > 0 ? (
          <div className="space-y-3">
            {associations.map((association) => {
              const draft = drafts[association.supplier_id] ?? toDraft(association);

              return (
                <div
                  key={association.id}
                  className="grid gap-3 rounded-xl border border-border/70 bg-card/80 p-4 md:grid-cols-[minmax(0,1.5fr)_1fr_1fr_auto_auto_auto]"
                >
                  <div>
                    <div className="font-medium">{association.supplier_name}</div>
                    <div className="text-xs text-muted-foreground">
                      {association.is_default ? t("defaultBadge") : t("secondaryBadge")}
                    </div>
                  </div>

                  <label className="space-y-2 text-sm">
                    <span>{t("unitCost")}</span>
                    <Input
                      value={draft.unitCost}
                      onChange={(event) => handleDraftChange(association.supplier_id, "unitCost", event.target.value)}
                      aria-label={`${association.supplier_name} ${t("unitCost")}`}
                    />
                  </label>

                  <label className="space-y-2 text-sm">
                    <span>{t("leadTimeDays")}</span>
                    <Input
                      value={draft.leadTimeDays}
                      onChange={(event) => handleDraftChange(association.supplier_id, "leadTimeDays", event.target.value)}
                      aria-label={`${association.supplier_name} ${t("leadTimeDays")}`}
                    />
                  </label>

                  <Button type="button" variant="outline" onClick={() => void handleSave(association)} disabled={saving}>
                    {t("save")}
                  </Button>

                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void handleMakeDefault(association.supplier_id)}
                    disabled={saving || association.is_default}
                  >
                    {t("setDefault")}
                  </Button>

                  <Button type="button" variant="ghost" onClick={() => void handleRemove(association.supplier_id)} disabled={saving}>
                    {t("remove")}
                  </Button>
                </div>
              );
            })}
          </div>
        ) : null}
      </div>
    </SectionCard>
  );
}