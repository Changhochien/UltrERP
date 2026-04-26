/** Create RFQ page. */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { PageHeader } from "../../components/layout/PageLayout";
import { SupplierCombobox } from "../../domain/inventory/components/SupplierCombobox";
import { useToast } from "../../hooks/useToast";
import { useCreateRFQ } from "../../domain/procurement/hooks/useRFQ";
import { fetchSupplier } from "../../lib/api/inventory";
import { checkSupplierRFQControls } from "../../lib/api/procurement";
import { RFQ_DETAIL_ROUTE, RFQ_LIST_ROUTE } from "../../lib/routes";
import type {
  RFQItemPayload,
  RFQSupplierPayload,
  SupplierControlResult,
} from "../../domain/procurement/types";

function today(): string {
  return new Date().toISOString().split("T")[0];
}

export default function CreateRFQPage() {
  const { t } = useTranslation("procurement");
  const { t: tCommon } = useTranslation("common");
  const navigate = useNavigate();
  const toast = useToast();
  const { create, loading, error } = useCreateRFQ();

  const [company, setCompany] = useState("");
  const [currency, setCurrency] = useState("TWD");
  const [transactionDate, setTransactionDate] = useState(today());
  const [scheduleDate, setScheduleDate] = useState("");
  const [notes, setNotes] = useState("");
  const [terms, setTerms] = useState("");
  const [items, setItems] = useState<RFQItemPayload[]>([
    { item_code: "", item_name: "", description: "", qty: "", uom: "", warehouse: "" },
  ]);
  const [suppliers, setSuppliers] = useState<RFQSupplierPayload[]>([
    { supplier_id: null, supplier_name: "", contact_email: "", notes: "" },
  ]);
  const [supplierControlResults, setSupplierControlResults] = useState<Array<SupplierControlResult | null>>([null]);
  const [supplierControlLoading, setSupplierControlLoading] = useState<boolean[]>([false]);
  const [supplierControlErrors, setSupplierControlErrors] = useState<Array<string | null>>([null]);

  function addItem() {
    setItems((prev) => [
      ...prev,
      { item_code: "", item_name: "", description: "", qty: "", uom: "", warehouse: "" },
    ]);
  }

  function removeItem(idx: number) {
    setItems((prev) => prev.filter((_, i) => i !== idx));
  }

  function updateItem(idx: number, field: keyof RFQItemPayload, value: string) {
    setItems((prev) =>
      prev.map((item, i) => (i === idx ? { ...item, [field]: value } : item)),
    );
  }

  function addSupplier() {
    setSuppliers((prev) => [
      ...prev,
      { supplier_id: null, supplier_name: "", contact_email: "", notes: "" },
    ]);
    setSupplierControlResults((prev) => [...prev, null]);
    setSupplierControlLoading((prev) => [...prev, false]);
    setSupplierControlErrors((prev) => [...prev, null]);
  }

  function removeSupplier(idx: number) {
    setSuppliers((prev) => prev.filter((_, i) => i !== idx));
    setSupplierControlResults((prev) => prev.filter((_, i) => i !== idx));
    setSupplierControlLoading((prev) => prev.filter((_, i) => i !== idx));
    setSupplierControlErrors((prev) => prev.filter((_, i) => i !== idx));
  }

  function updateSupplier(idx: number, field: keyof RFQSupplierPayload, value: string) {
    setSuppliers((prev) =>
      prev.map((s, i) => (i === idx ? { ...s, [field]: value } : s)),
    );
  }

  function setSupplierControlResult(idx: number, result: SupplierControlResult | null) {
    setSupplierControlResults((prev) => prev.map((entry, i) => (i === idx ? result : entry)));
  }

  function setSupplierControlCheckLoading(idx: number, isLoading: boolean) {
    setSupplierControlLoading((prev) => prev.map((entry, i) => (i === idx ? isLoading : entry)));
  }

  function setSupplierControlError(idx: number, message: string | null) {
    setSupplierControlErrors((prev) => prev.map((entry, i) => (i === idx ? message : entry)));
  }

  function clearSupplierSelection(idx: number) {
    setSuppliers((prev) =>
      prev.map((supplier, i) => (
        i === idx
          ? {
              ...supplier,
              supplier_id: null,
              supplier_name: "",
              contact_email: "",
            }
          : supplier
      )),
    );
    setSupplierControlResult(idx, null);
    setSupplierControlCheckLoading(idx, false);
    setSupplierControlError(idx, null);
  }

  async function evaluateSupplierControl(idx: number, supplierId: string) {
    setSupplierControlCheckLoading(idx, true);
    setSupplierControlError(idx, null);
    try {
      const result = await checkSupplierRFQControls(supplierId);
      setSupplierControlResult(idx, result);
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : t("rfq.supplierControlCheckError");
      setSupplierControlResult(idx, null);
      setSupplierControlError(idx, message);
      throw err;
    } finally {
      setSupplierControlCheckLoading(idx, false);
    }
  }

  async function handleSupplierSelected(idx: number, supplierId: string) {
    try {
      const [supplierResponse, controlResult] = await Promise.all([
        fetchSupplier(supplierId),
        evaluateSupplierControl(idx, supplierId),
      ]);

      if (!supplierResponse.ok) {
        throw new Error(supplierResponse.error);
      }

      const supplier = supplierResponse.data;
      setSuppliers((prev) =>
        prev.map((entry, i) => (
          i === idx
            ? {
                ...entry,
                supplier_id: supplier.id,
                supplier_name: supplier.name,
                contact_email: supplier.contact_email ?? "",
              }
            : entry
        )),
      );

      if (controlResult.is_blocked) {
        toast({ title: controlResult.reason, variant: "destructive" });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : t("rfq.supplierControlCheckError");
      clearSupplierSelection(idx);
      setSupplierControlError(idx, message);
      toast({ title: message, variant: "destructive" });
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!company) {
      toast({ title: tCommon("validation.required", { field: t("rfq.fields.company") }), variant: "destructive" });
      return;
    }
    if (items.every((i) => !i.item_name && !i.item_code)) {
      toast({ title: tCommon("validation.requiredItems"), variant: "destructive" });
      return;
    }

    const supplierEntries = suppliers
      .map((supplier, idx) => ({ supplier, idx }))
      .filter(({ supplier }) => supplier.supplier_name || supplier.supplier_id);

    if (supplierControlLoading.some(Boolean)) {
      toast({ title: t("rfq.supplierControlChecking"), variant: "destructive" });
      return;
    }

    try {
      const latestControlResults = await Promise.all(
        supplierEntries.map(async ({ supplier, idx }) => {
          if (!supplier.supplier_id) {
            return supplierControlResults[idx];
          }
          return evaluateSupplierControl(idx, supplier.supplier_id);
        }),
      );

      const blockedResult = latestControlResults.find((result) => result?.is_blocked);
      if (blockedResult) {
        toast({ title: blockedResult.reason, variant: "destructive" });
        return;
      }

      const rfq = await create({
        company,
        currency,
        transaction_date: transactionDate,
        schedule_date: scheduleDate || null,
        notes,
        terms_and_conditions: terms,
        items: items.filter((i) => i.item_name || i.item_code),
        suppliers: supplierEntries.map(({ supplier }) => supplier),
      });
      toast({ title: t("rfq.created"), variant: "success" });
      navigate(`${RFQ_DETAIL_ROUTE.replace(":rfqId", rfq.id)}`);
    } catch (err) {
      toast({
        title: err instanceof Error ? err.message : t("rfq.createError"),
        variant: "destructive",
      });
    }
  }

  const hasBlockedSupplier = suppliers.some(
    (supplier, idx) => Boolean(supplier.supplier_id && supplierControlResults[idx]?.is_blocked),
  );
  const supplierChecksPending = supplierControlLoading.some(Boolean);

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("rfq.create")}
        description={t("rfq.createDescription")}
      />

      <form onSubmit={handleSubmit} className="space-y-8 max-w-3xl">
        {/* Header fields */}
        <div className="rounded-lg border bg-card p-6 space-y-4">
          <h2 className="text-lg font-semibold">{t("rfq.sectionHeader")}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">{t("rfq.fields.company")} *</label>
              <Input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder={t("rfq.fields.companyPlaceholder")}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">{t("rfq.fields.currency")}</label>
              <Input
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                maxLength={3}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">{t("rfq.fields.transactionDate")}</label>
              <Input
                type="date"
                value={transactionDate}
                onChange={(e) => setTransactionDate(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">{t("rfq.fields.scheduleDate")}</label>
              <Input
                type="date"
                value={scheduleDate}
                onChange={(e) => setScheduleDate(e.target.value)}
                className="mt-1"
              />
            </div>
          </div>
        </div>

        {/* Items */}
        <div className="rounded-lg border bg-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">{t("rfq.items")}</h2>
            <Button type="button" variant="outline" size="sm" onClick={addItem}>
              {t("rfq.addItem")}
            </Button>
          </div>
          {items.map((item, idx) => (
            <div key={idx} className="grid grid-cols-1 sm:grid-cols-6 gap-2 p-3 border rounded-md">
              <div className="sm:col-span-2">
                <label className="text-xs text-muted-foreground">{t("rfq.fields.itemCode")}</label>
                <Input
                  value={item.item_code}
                  onChange={(e) => updateItem(idx, "item_code", e.target.value)}
                  placeholder={t("rfq.fields.itemCodePlaceholder")}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs text-muted-foreground">{t("rfq.fields.itemName")}</label>
                <Input
                  value={item.item_name}
                  onChange={(e) => updateItem(idx, "item_name", e.target.value)}
                  placeholder={t("rfq.fields.itemNamePlaceholder")}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">{t("rfq.fields.qty")}</label>
                <Input
                  type="number"
                  value={item.qty}
                  onChange={(e) => updateItem(idx, "qty", e.target.value)}
                  min="0"
                />
              </div>
              <div className="flex items-end gap-1">
                <Input
                  value={item.uom}
                  onChange={(e) => updateItem(idx, "uom", e.target.value)}
                  placeholder={t("rfq.fields.uom")}
                  className="flex-1"
                />
                {items.length > 1 && (
                  <Button type="button" variant="ghost" size="sm" onClick={() => removeItem(idx)}>
                    ×
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Suppliers */}
        <div className="rounded-lg border bg-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">{t("rfq.suppliers")}</h2>
            <Button type="button" variant="outline" size="sm" onClick={addSupplier}>
              {t("rfq.addSupplier")}
            </Button>
          </div>
          <p className="text-sm text-muted-foreground">{t("rfq.supplierMasterHint")}</p>
          {suppliers.map((supp, idx) => (
            <div key={idx} className="space-y-3 p-3 border rounded-md">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <div>
                  <label className="text-xs text-muted-foreground">{t("rfq.fields.supplierName")}</label>
                  <SupplierCombobox
                    value={supp.supplier_id ?? ""}
                    onChange={(supplierId) => void handleSupplierSelected(idx, supplierId)}
                    onClear={() => clearSupplierSelection(idx)}
                    placeholder={t("rfq.fields.supplierNamePlaceholder")}
                    ariaLabel={t("rfq.fields.supplierName")}
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">{t("rfq.fields.contactEmail")}</label>
                  <Input
                    type="email"
                    value={supp.contact_email}
                    onChange={(e) => updateSupplier(idx, "contact_email", e.target.value)}
                    placeholder="supplier@example.com"
                  />
                </div>
                <div className="flex items-end">
                  <Input
                    value={supp.notes}
                    onChange={(e) => updateSupplier(idx, "notes", e.target.value)}
                    placeholder={t("rfq.fields.notes")}
                    className="flex-1"
                  />
                  {suppliers.length > 1 && (
                    <Button type="button" variant="ghost" size="sm" onClick={() => removeSupplier(idx)}>
                      ×
                    </Button>
                  )}
                </div>
              </div>

              {supplierControlLoading[idx] ? (
                <p className="text-sm text-muted-foreground">{t("rfq.supplierControlChecking")}</p>
              ) : null}

              {supplierControlErrors[idx] ? (
                <p className="text-sm text-destructive">{supplierControlErrors[idx]}</p>
              ) : null}

              {supplierControlResults[idx]?.reason ? (
                <div
                  role="alert"
                  className={
                    supplierControlResults[idx]?.is_blocked
                      ? "rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
                      : "rounded-md border border-amber-300/60 bg-amber-50 px-3 py-2 text-sm text-amber-900"
                  }
                >
                  <p className="font-medium">
                    {supplierControlResults[idx]?.is_blocked
                      ? t("rfq.supplierControlBlocked")
                      : t("rfq.supplierControlWarning")}
                  </p>
                  <p>{supplierControlResults[idx]?.reason}</p>
                </div>
              ) : null}
            </div>
          ))}
        </div>

        {/* Terms */}
        <div className="rounded-lg border bg-card p-6 space-y-4">
          <h2 className="text-lg font-semibold">{t("rfq.terms")}</h2>
          <div>
            <label className="text-sm font-medium">{t("rfq.fields.terms")}</label>
            <textarea
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              rows={4}
              value={terms}
              onChange={(e) => setTerms(e.target.value)}
              placeholder={t("rfq.termsPlaceholder")}
            />
          </div>
          <div>
            <label className="text-sm font-medium">{t("rfq.fields.notes")}</label>
            <textarea
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={t("rfq.notesPlaceholder")}
            />
          </div>
        </div>

        {error && <p className="text-destructive text-sm">{error}</p>}

        <div className="flex gap-3">
          <Button type="submit" disabled={loading || supplierChecksPending || hasBlockedSupplier}>
            {loading ? tCommon("status.saving") : t("rfq.save")}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate(RFQ_LIST_ROUTE)}>
            {tCommon("actions.cancel")}
          </Button>
        </div>
      </form>
    </div>
  );
}
