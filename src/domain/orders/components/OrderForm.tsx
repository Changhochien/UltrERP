/** Form to create a new sales order with dynamic line items. */

import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { SurfaceMessage } from "../../../components/layout/PageLayout";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { CustomerCombobox } from "../../../components/customers/CustomerCombobox";
import { ProductCombobox } from "../../../components/products/ProductCombobox";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../../components/ui/table";
import { usePaymentTerms, useCreateOrder } from "../hooks/useOrders";
import type { OrderCreatePayload, OrderLineCreate } from "../types";
import { trackEvent, AnalyticsEvents } from "../../../lib/analytics";

interface OrderFormProps {
  onCreated: (orderId: string) => void;
  onCancel: () => void;
}

function emptyLine(): OrderLineCreate {
  return { product_id: "", description: "", quantity: 1, list_unit_price: 0, unit_price: 0, discount_amount: 0, tax_policy_code: "standard" };
}

export function OrderForm({ onCreated, onCancel }: OrderFormProps) {
  const { t } = useTranslation("common");
  const { items: paymentTerms, loading: termsLoading, error: termsError } = usePaymentTerms();
  const { create, submitting, error } = useCreateOrder();

  const [customerId, setCustomerId] = useState("");
  const [paymentTermsCode, setPaymentTermsCode] = useState("NET_30");
  const [discountAmount, setDiscountAmount] = useState(0);
  const [discountPercent, setDiscountPercent] = useState(0);
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<OrderLineCreate[]>([emptyLine()]);
  const submittingRef = useRef(false);


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
        discount_amount: discountAmount || undefined,
        discount_percent: discountPercent || undefined,
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
            <CustomerCombobox
              value={customerId}
              onChange={setCustomerId}
              onClear={() => setCustomerId("")}
              placeholder={t("orders.form.customerPlaceholder") ?? "Search customer by name or BAN…"}
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

          <label className="space-y-2">
            <span>{t("orders.form.discountAmount")}</span>
            <Input
              id="ord-discount-amt"
              type="number"
              min={0}
              step="0.01"
              value={discountAmount}
              onChange={(e) => setDiscountAmount(Number(e.target.value))}
              placeholder="0.00"
            />
          </label>

          <label className="space-y-2">
            <span>{t("orders.form.discountPercent")} (%)</span>
            <Input
              id="ord-discount-pct"
              type="number"
              min={0}
              max={100}
              step="0.01"
              value={discountPercent}
              onChange={(e) => setDiscountPercent(Number(e.target.value))}
              placeholder="0.00"
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
                <TableHead>{t("orders.form.discount")}</TableHead>
                <TableHead>{t("orders.form.taxPolicy")}</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {lines.map((line, idx) => (
                <TableRow key={idx}>
                  <TableCell>
                    <ProductCombobox
                      value={line.product_id ?? ""}
                      onChange={(productId) => updateLine(idx, { product_id: productId })}
                      onProductSelected={(product) => updateLine(idx, { description: product.name })}
                      placeholder="Search product…"
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
                    <Input
                      type="number"
                      min={0}
                      step="0.01"
                      value={line.discount_amount ?? 0}
                      onChange={(e) => updateLine(idx, { discount_amount: Number(e.target.value) })}
                      aria-label={`Line ${idx + 1} discount`}
                      className="w-24"
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
