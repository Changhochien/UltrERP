/** Create RFQ page. */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { PageHeader } from "../../components/layout/PageLayout";
import { useToast } from "../../hooks/useToast";
import { useCreateRFQ } from "../../domain/procurement/hooks/useRFQ";
import { RFQ_DETAIL_ROUTE, RFQ_LIST_ROUTE } from "../../lib/routes";
import type { RFQItemPayload, RFQSupplierPayload } from "../../domain/procurement/types";

function today(): string {
  return new Date().toISOString().split("T")[0];
}

export default function CreateRFQPage() {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const { toast } = useToast();
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
  }

  function removeSupplier(idx: number) {
    setSuppliers((prev) => prev.filter((_, i) => i !== idx));
  }

  function updateSupplier(idx: number, field: keyof RFQSupplierPayload, value: string) {
    setSuppliers((prev) =>
      prev.map((s, i) => (i === idx ? { ...s, [field]: value } : s)),
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!company) {
      toast({ title: t("common.validation.required", { field: t("procurement.rfq.fields.company") }), variant: "destructive" });
      return;
    }
    if (items.every((i) => !i.item_name && !i.item_code)) {
      toast({ title: t("common.validation.requiredItems"), variant: "destructive" });
      return;
    }
    try {
      const rfq = await create({
        company,
        currency,
        transaction_date: transactionDate,
        schedule_date: scheduleDate || null,
        notes,
        terms_and_conditions: terms,
        items: items.filter((i) => i.item_name || i.item_code),
        suppliers: suppliers.filter((s) => s.supplier_name),
      });
      toast({ title: t("procurement.rfq.created"), variant: "success" });
      navigate(`${RFQ_DETAIL_ROUTE.replace(":rfqId", rfq.id)}`);
    } catch {
      toast({ title: t("procurement.rfq.createError"), variant: "destructive" });
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("procurement.rfq.create")}
        description={t("procurement.rfq.createDescription")}
      />

      <form onSubmit={handleSubmit} className="space-y-8 max-w-3xl">
        {/* Header fields */}
        <div className="rounded-lg border bg-card p-6 space-y-4">
          <h2 className="text-lg font-semibold">{t("procurement.rfq.sectionHeader")}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">{t("procurement.rfq.fields.company")} *</label>
              <Input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder={t("procurement.rfq.fields.companyPlaceholder")}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">{t("procurement.rfq.fields.currency")}</label>
              <Input
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                maxLength={3}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">{t("procurement.rfq.fields.transactionDate")}</label>
              <Input
                type="date"
                value={transactionDate}
                onChange={(e) => setTransactionDate(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">{t("procurement.rfq.fields.scheduleDate")}</label>
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
            <h2 className="text-lg font-semibold">{t("procurement.rfq.items")}</h2>
            <Button type="button" variant="outline" size="sm" onClick={addItem}>
              {t("procurement.rfq.addItem")}
            </Button>
          </div>
          {items.map((item, idx) => (
            <div key={idx} className="grid grid-cols-1 sm:grid-cols-6 gap-2 p-3 border rounded-md">
              <div className="sm:col-span-2">
                <label className="text-xs text-muted-foreground">{t("procurement.rfq.fields.itemCode")}</label>
                <Input
                  value={item.item_code}
                  onChange={(e) => updateItem(idx, "item_code", e.target.value)}
                  placeholder={t("procurement.rfq.fields.itemCodePlaceholder")}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs text-muted-foreground">{t("procurement.rfq.fields.itemName")}</label>
                <Input
                  value={item.item_name}
                  onChange={(e) => updateItem(idx, "item_name", e.target.value)}
                  placeholder={t("procurement.rfq.fields.itemNamePlaceholder")}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">{t("procurement.rfq.fields.qty")}</label>
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
                  placeholder={t("procurement.rfq.fields.uom")}
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
            <h2 className="text-lg font-semibold">{t("procurement.rfq.suppliers")}</h2>
            <Button type="button" variant="outline" size="sm" onClick={addSupplier}>
              {t("procurement.rfq.addSupplier")}
            </Button>
          </div>
          {suppliers.map((supp, idx) => (
            <div key={idx} className="grid grid-cols-1 sm:grid-cols-3 gap-2 p-3 border rounded-md">
              <div>
                <label className="text-xs text-muted-foreground">{t("procurement.rfq.fields.supplierName")}</label>
                <Input
                  value={supp.supplier_name}
                  onChange={(e) => updateSupplier(idx, "supplier_name", e.target.value)}
                  placeholder={t("procurement.rfq.fields.supplierNamePlaceholder")}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">{t("procurement.rfq.fields.contactEmail")}</label>
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
                  placeholder={t("procurement.rfq.fields.notes")}
                  className="flex-1"
                />
                {suppliers.length > 1 && (
                  <Button type="button" variant="ghost" size="sm" onClick={() => removeSupplier(idx)}>
                    ×
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Terms */}
        <div className="rounded-lg border bg-card p-6 space-y-4">
          <h2 className="text-lg font-semibold">{t("procurement.rfq.terms")}</h2>
          <div>
            <label className="text-sm font-medium">{t("procurement.rfq.fields.terms")}</label>
            <textarea
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              rows={4}
              value={terms}
              onChange={(e) => setTerms(e.target.value)}
              placeholder={t("procurement.rfq.fields.termsPlaceholder")}
            />
          </div>
          <div>
            <label className="text-sm font-medium">{t("procurement.rfq.fields.notes")}</label>
            <textarea
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={t("procurement.rfq.fields.notesPlaceholder")}
            />
          </div>
        </div>

        {error && <p className="text-destructive text-sm">{error}</p>}

        <div className="flex gap-3">
          <Button type="submit" disabled={loading}>
            {loading ? t("common.status.saving") : t("procurement.rfq.save")}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate(RFQ_LIST_ROUTE)}>
            {t("common.actions.cancel")}
          </Button>
        </div>
      </form>
    </div>
  );
}
