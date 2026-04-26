/** RFQ detail page with supplier quotation comparison. */

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { PageHeader } from "../../components/layout/PageLayout";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useToast } from "../../hooks/useToast";
import { useRFQ, useRFQComparison, useSubmitRFQ } from "../../domain/procurement/hooks/useRFQ";
import {
  useAward,
  useRFQAward,
} from "../../domain/procurement/hooks/useSupplierQuotation";
import { createSupplierQuotation } from "../../lib/api/procurement";
import { buildCreatePurchaseOrderPath } from "../../lib/routes";

export function RFQDetailPage() {
  const { t } = useTranslation("procurement");
  const { t: tCommon } = useTranslation("common");
  const { rfqId } = useParams<{ rfqId: string }>();
  const { success: toastSuccess, error: toastError } = useToast();

  const { rfq, loading, error, refetch } = useRFQ(rfqId);
  const { data: comparison, refetch: refetchComparison } = useRFQComparison(rfqId);
  const { award: awardQuotation, loading: awarding } = useAward();
  const { award: existingAward, refetch: refetchAward } = useRFQAward(rfqId);
  const { submit, loading: submitting } = useSubmitRFQ();

  const [activeTab, setActiveTab] = useState<"items" | "suppliers" | "compare">("items");
  const [showAddQuotation, setShowAddQuotation] = useState(false);
  const [quotationForm, setQuotationForm] = useState({
    supplier_name: "",
    valid_till: "",
    lead_time_days: "",
    grand_total: "",
    notes: "",
  });
  const [creatingSQ, setCreatingSQ] = useState(false);

  if (loading) return <p className="text-muted-foreground">{tCommon("status.loading")}</p>;
  if (error) return <p className="text-destructive">{error}</p>;
  if (!rfq) return null;

  async function handleSubmitRFQ() {
    try {
      await submit(rfqId!);
      toastSuccess(t("rfq.submitted"));
      refetch();
    } catch {
      toastError(t("rfq.submitError"));
    }
  }

  async function handleCreateQuotation() {
    if (!quotationForm.supplier_name) {
      toastError(tCommon("validation.required", { field: t("rfq.fields.supplierName") }));
      return;
    }
    setCreatingSQ(true);
    try {
      const items = (comparison?.items ?? []).map((rfqItem) => ({
        rfq_item_id: rfqItem.id,
        item_code: rfqItem.item_code,
        item_name: rfqItem.item_name,
        description: rfqItem.description,
        qty: rfqItem.qty,
        uom: rfqItem.uom,
        unit_rate: "0",
        amount: "0",
        tax_rate: "0",
        tax_amount: "0",
        tax_code: "",
        normalized_unit_rate: "0",
        normalized_amount: "0",
      }));
      await createSupplierQuotation({
        rfq_id: rfqId,
        supplier_name: quotationForm.supplier_name,
        company: rfq!.company,
        currency: rfq!.currency,
        transaction_date: new Date().toISOString().split("T")[0],
        valid_till: quotationForm.valid_till || null,
        lead_time_days: quotationForm.lead_time_days ? Number(quotationForm.lead_time_days) : null,
        grand_total: quotationForm.grand_total || "0",
        base_grand_total: quotationForm.grand_total || "0",
        comparison_base_total: quotationForm.grand_total || "0",
        subtotal: quotationForm.grand_total || "0",
        total_taxes: "0",
        taxes: [],
        contact_person: "",
        contact_email: "",
        terms_and_conditions: "",
        notes: quotationForm.notes,
        items,
      });
      toastSuccess(t("sq.created"));
      setShowAddQuotation(false);
      refetchComparison();
      refetch();
    } catch {
      toastError(t("sq.createError"));
    } finally {
      setCreatingSQ(false);
    }
  }

  async function handleAward(quotationId: string) {
    try {
      await awardQuotation({ rfq_id: rfqId!, quotation_id: quotationId, awarded_by: "buyer" });
      toastSuccess(t("award.success"));
      refetchComparison();
      refetchAward();
    } catch {
      toastError(t("award.error"));
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={rfq ? (rfq.name || t("rfq.title")) : t("rfq.title")}
        description={rfq ? `${t("rfq.fields.status")}: ${rfq.status}` : ""}
      />

      <div className="flex items-center gap-3">
        <StatusBadge status={rfq.status} />
        {rfq.status === "draft" && (
          <Button size="sm" onClick={handleSubmitRFQ} disabled={submitting}>
            {submitting ? tCommon("status.saving") : t("rfq.submit")}
          </Button>
        )}
        {rfq.status === "submitted" && !existingAward && (
          <Button size="sm" variant="outline" onClick={() => setShowAddQuotation(true)}>
            {t("sq.add")}
          </Button>
        )}
        <Button size="sm" variant="outline" onClick={() => refetch()}>
          {tCommon("actions.refresh")}
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {(["items", "suppliers", "compare"] as const).map((tab) => (
          <button
            key={tab}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
            onClick={() => setActiveTab(tab)}
          >
            {t(`procurement.rfq.tabs.${tab}`)}
          </button>
        ))}
      </div>

      {/* Items Tab */}
      {activeTab === "items" && (
        <div className="rounded-lg border bg-card">
          {rfq.items.length === 0 ? (
            <p className="p-6 text-muted-foreground text-center">{t("rfq.noItems")}</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/30 text-left text-muted-foreground">
                  <th className="p-3 font-medium">#</th>
                  <th className="p-3 font-medium">{t("rfq.fields.itemCode")}</th>
                  <th className="p-3 font-medium">{t("rfq.fields.itemName")}</th>
                  <th className="p-3 font-medium">{t("rfq.fields.qty")}</th>
                  <th className="p-3 font-medium">{t("rfq.fields.uom")}</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rfq.items.map((item) => (
                  <tr key={item.id}>
                    <td className="p-3 text-muted-foreground">{item.idx + 1}</td>
                    <td className="p-3 font-medium">{item.item_code || "—"}</td>
                    <td className="p-3">{item.item_name}</td>
                    <td className="p-3">{item.qty}</td>
                    <td className="p-3">{item.uom || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Suppliers Tab */}
      {activeTab === "suppliers" && (
        <div className="rounded-lg border bg-card">
          {rfq.suppliers.length === 0 ? (
            <p className="p-6 text-muted-foreground text-center">{t("rfq.noSuppliers")}</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/30 text-left text-muted-foreground">
                  <th className="p-3 font-medium">{t("rfq.fields.supplierName")}</th>
                  <th className="p-3 font-medium">{t("rfq.fields.contactEmail")}</th>
                  <th className="p-3 font-medium">{t("rfq.fields.quoteStatus")}</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rfq.suppliers.map((supp) => (
                  <tr key={supp.id}>
                    <td className="p-3 font-medium">{supp.supplier_name}</td>
                    <td className="p-3">{supp.contact_email || "—"}</td>
                    <td className="p-3">
                      <Badge
                        variant={
                          supp.quote_status === "received"
                            ? "default"
                            : supp.quote_status === "lost"
                            ? "destructive"
                            : "secondary"
                        }
                      >
                        {t(`procurement.rfq.quoteStatus.${supp.quote_status}`)}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Compare Tab */}
      {activeTab === "compare" && (
        <div className="space-y-4">
          {existingAward && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm font-medium text-emerald-800">
                  {t("award.selected", { supplier: existingAward.awarded_supplier_name })}
                </p>
                <Link
                  to={buildCreatePurchaseOrderPath(existingAward.id)}
                  className="inline-flex items-center rounded-md border border-emerald-300 bg-white px-3 py-1.5 text-sm font-medium text-emerald-700 hover:bg-emerald-100"
                >
                  {t("award.createPurchaseOrder")}
                </Link>
              </div>
            </div>
          )}

          {comparison && comparison.quotations.length === 0 ? (
            <div className="rounded-lg border bg-card p-12 text-center">
              <p className="text-muted-foreground">{t("rfq.noQuotations")}</p>
              <Button className="mt-4" onClick={() => setShowAddQuotation(true)}>
                {t("sq.add")}
              </Button>
            </div>
          ) : (
            comparison?.quotations.map((row) => (
              <div
                key={row.quotation_id}
                className={`rounded-lg border p-4 ${
                  row.is_awarded
                    ? "border-emerald-400 bg-emerald-50"
                    : row.is_expired
                    ? "border-red-200 bg-red-50 opacity-60"
                    : "bg-card"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <h3 className="font-semibold">{row.supplier_name}</h3>
                    <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                      <span>
                        {t("sq.fields.grandTotal")}:{" "}
                        <strong className="text-foreground">
                          {row.currency} {Number(row.comparison_base_total).toLocaleString()}
                        </strong>
                      </span>
                      {row.lead_time_days != null && (
                        <span>
                          {t("sq.fields.leadTime")}: <strong>{row.lead_time_days}d</strong>
                        </span>
                      )}
                      {row.valid_till && (
                        <span>
                          {t("sq.fields.validTill")}: <strong>{row.valid_till}</strong>
                        </span>
                      )}
                      {row.is_expired && (
                        <Badge variant="destructive">{t("sq.expired")}</Badge>
                      )}
                      {row.is_awarded && (
                        <Badge variant="default">{t("award.winner")}</Badge>
                      )}
                    </div>
                  </div>
                  {!row.is_expired && !existingAward && (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={awarding}
                      onClick={() => handleAward(row.quotation_id)}
                    >
                      {t("award.selectAsWinner")}
                    </Button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Add Quotation Dialog */}
      {showAddQuotation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-lg rounded-xl border bg-card p-6 shadow-xl space-y-4 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold">{t("sq.add")}</h2>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium">{t("rfq.fields.supplierName")} *</label>
                <Input
                  value={quotationForm.supplier_name}
                  onChange={(e) => setQuotationForm((p) => ({ ...p, supplier_name: e.target.value }))}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-medium">{t("sq.fields.validTill")}</label>
                  <Input
                    type="date"
                    value={quotationForm.valid_till}
                    onChange={(e) => setQuotationForm((p) => ({ ...p, valid_till: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">{t("sq.fields.leadTimeDays")}</label>
                  <Input
                    type="number"
                    value={quotationForm.lead_time_days}
                    onChange={(e) => setQuotationForm((p) => ({ ...p, lead_time_days: e.target.value }))}
                    placeholder="e.g. 14"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium">{t("sq.fields.grandTotal")}</label>
                <Input
                  type="number"
                  value={quotationForm.grand_total}
                  onChange={(e) => setQuotationForm((p) => ({ ...p, grand_total: e.target.value }))}
                  placeholder="0.00"
                />
              </div>
              <div>
                <label className="text-sm font-medium">{t("rfq.fields.notes")}</label>
                <textarea
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  rows={3}
                  value={quotationForm.notes}
                  onChange={(e) => setQuotationForm((p) => ({ ...p, notes: e.target.value }))}
                />
              </div>
            </div>
            <div className="flex gap-3">
              <Button onClick={handleCreateQuotation} disabled={creatingSQ}>
                {creatingSQ ? tCommon("status.saving") : t("sq.save")}
              </Button>
              <Button variant="outline" onClick={() => setShowAddQuotation(false)}>
                {tCommon("actions.cancel")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
