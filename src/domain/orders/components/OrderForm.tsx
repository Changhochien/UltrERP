/** Form to create a new sales order with dynamic line items. */

import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { SurfaceMessage } from "../../../components/layout/PageLayout";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../../components/ui/table";
import { usePaymentTerms, useCreateOrder } from "../hooks/useOrders";
import { useStockCheck } from "../hooks/useStockCheck";
import type { OrderCreatePayload, OrderLineCreate } from "../types";
import { trackEvent, AnalyticsEvents } from "../../../lib/analytics";

interface OrderFormProps {
  onCreated: (orderId: string) => void;
  onCancel: () => void;
}

function emptyLine(): OrderLineCreate {
  return { product_id: "", description: "", quantity: 1, unit_price: 0, tax_policy_code: "standard" };
}

export function OrderForm({ onCreated, onCancel }: OrderFormProps) {
  const { t } = useTranslation("common");
  const { items: paymentTerms, loading: termsLoading, error: termsError } = usePaymentTerms();
  const { create, submitting, error } = useCreateOrder();
  const { stockData, stockLoading, checkProductStock } = useStockCheck();

  const [customerId, setCustomerId] = useState("");
  const [paymentTermsCode, setPaymentTermsCode] = useState("NET_30");
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<OrderLineCreate[]>([emptyLine()]);
  const submittingRef = useRef(false);

  const productIdKey = lines.map((l) => l.product_id).join(",");

  useEffect(() => {
    for (const pid of productIdKey.split(",")) {
      if (pid && pid.length >= 36) {
        checkProductStock(pid);
      }
    }
  }, [productIdKey, checkProductStock]);

  if (termsLoading) return <p aria-busy="true">{t("orders.form.loading")}</p>;
  if (termsError) return <div role="alert" className="text-sm text-destructive">{termsError}</div>;

  const updateLine = (idx: number, patch: Partial<OrderLineCreate>) => {
    setLines((prev) =>
      prev.map((l, i) => (i === idx ? { ...l, ...patch } : l)),
    );
  };

  const removeLine = (idx: number) => {
    setLines((prev) => prev.filter((_, i) => i !== idx));
  };

  const validLines = lines.filter(
    (l) => l.product_id && l.description && l.quantity > 0,
  );
  const hasInvalidLines = lines.length > 0 && validLines.length < lines.length;
  const canSubmit = customerId && validLines.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submittingRef.current) return;
    submittingRef.current = true;
    try {
      const payload: OrderCreatePayload = {
        customer_id: customerId,
        payment_terms_code: paymentTermsCode as OrderCreatePayload["payment_terms_code"],
        notes: notes || undefined,
        lines: validLines,
      };
      const result = await create(payload);
      if (result) {
        trackEvent(AnalyticsEvents.ORDER_CREATED, { source_page: "/orders" });
        onCreated(result.id);
      }
    } finally {
      submittingRef.current = false;
    }
  };

  return (
    <section aria-label="Create order" className="space-y-5">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold tracking-tight">{t("orders.form.newOrderTitle")}</h2>
        <p className="text-sm text-muted-foreground">{t("orders.form.newOrderDescription")}</p>
      </div>

      {error ? <SurfaceMessage tone="danger">{error}</SurfaceMessage> : null}

      <form onSubmit={(e) => void handleSubmit(e)} aria-label="Order form" className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <label className="space-y-2">
            <span>{t("orders.form.customerId")}</span>
            <Input
              id="ord-customer"
              type="text"
              required
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              placeholder="Customer UUID"
            />
          </label>

          <label className="space-y-2">
            <span>{t("orders.form.paymentTerms")}</span>
            <select id="ord-terms" value={paymentTermsCode} onChange={(e) => setPaymentTermsCode(e.target.value)}>
              {paymentTerms.map((t) => (
                <option key={t.code} value={t.code}>{t.label}</option>
              ))}
            </select>
          </label>

          <label className="space-y-2">
            <span>{t("orders.form.notes")}</span>
            <Input
              id="ord-notes"
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional notes"
            />
          </label>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-border/80 bg-card/90 shadow-sm">
          <Table aria-label="Order line items" className="min-w-[640px]">
            <TableHeader>
              <TableRow>
                <TableHead>{t("orders.form.productId")}</TableHead>
                <TableHead>{t("orders.form.description")}</TableHead>
                <TableHead>{t("orders.form.quantity")}</TableHead>
                <TableHead>{t("orders.form.unitPrice")}</TableHead>
                <TableHead>{t("orders.form.taxPolicy")}</TableHead>
                <TableHead>{t("orders.form.stock")}</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {lines.map((line, idx) => (
                <TableRow key={idx}>
                  <TableCell>
                    <Input
                      type="text"
                      required
                      value={line.product_id}
                      onChange={(e) => updateLine(idx, { product_id: e.target.value })}
                      placeholder="Product UUID"
                      aria-label={`Line ${idx + 1} product`}
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      type="text"
                      required
                      value={line.description}
                      onChange={(e) => updateLine(idx, { description: e.target.value })}
                      placeholder="Description"
                      aria-label={`Line ${idx + 1} description`}
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      required
                      min={1}
                      step="any"
                      value={line.quantity}
                      onChange={(e) => updateLine(idx, { quantity: Number(e.target.value) })}
                      aria-label={`Line ${idx + 1} quantity`}
                      className="w-24"
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      required
                      min={0}
                      step="0.01"
                      value={line.unit_price}
                      onChange={(e) => updateLine(idx, { unit_price: Number(e.target.value) })}
                      aria-label={`Line ${idx + 1} unit price`}
                      className="w-28"
                    />
                  </TableCell>
                  <TableCell>
                    <select
                      value={line.tax_policy_code}
                      onChange={(e) => updateLine(idx, { tax_policy_code: e.target.value as OrderLineCreate["tax_policy_code"] })}
                      aria-label={`Line ${idx + 1} tax policy`}
                    >
                      <option value="standard">{t("orders.form.taxPolicyStandard")}</option>
                      <option value="zero">{t("orders.form.taxPolicyZero")}</option>
                      <option value="exempt">{t("orders.form.taxPolicyExempt")}</option>
                      <option value="special">Special</option>
                    </select>
                  </TableCell>
                  <TableCell>
                    {(() => {
                      const pid = line.product_id;
                      if (!pid || pid.length < 36) return null;
                      if (stockLoading[pid]) return <span aria-busy="true">…</span>;
                      const info = stockData[pid];
                      if (!info) return null;
                      const avail = info.total_available;
                      const insufficient = line.quantity > avail;
                      return (
                        <span aria-label={t("orders.form.lineStock", { index: idx + 1 })} className={insufficient ? "font-semibold text-destructive" : "font-semibold text-success-token"}>
                          {avail} avail
                          {insufficient ? (
                            <span className="block text-xs font-normal text-destructive">Insufficient stock: {avail} units available</span>
                          ) : null}
                        </span>
                      );
                    })()}
                  </TableCell>
                  <TableCell>
                    {lines.length > 1 ? (
                      <Button type="button" variant="ghost" size="sm" onClick={() => removeLine(idx)} aria-label={`Remove line ${idx + 1}`}>
                        {t("common.delete")}
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        <Button type="button" variant="outline" onClick={() => setLines((prev) => [...prev, emptyLine()])}>
          {t("orders.form.addLine")}
        </Button>

        {hasInvalidLines ? (
          <SurfaceMessage tone="warning">
            {lines.length - validLines.length} line(s) incomplete — fill in product ID, description, and quantity (&gt; 0).
          </SurfaceMessage>
        ) : null}

        <div className="flex gap-3">
          <Button type="submit" disabled={!canSubmit || submitting}>
            {submitting ? t("orders.form.creating") : t("orders.form.createOrder")}
          </Button>
          <Button type="button" variant="outline" onClick={onCancel}>
            {t("common.cancel")}
          </Button>
        </div>
      </form>
    </section>
  );
}
