/** Form to create a new sales order with dynamic line items. */

import { useEffect, useState } from "react";
import { usePaymentTerms, useCreateOrder } from "../hooks/useOrders";
import { useStockCheck } from "../hooks/useStockCheck";
import type { OrderCreatePayload, OrderLineCreate } from "../types";

interface OrderFormProps {
  onCreated: (orderId: string) => void;
  onCancel: () => void;
}

function emptyLine(): OrderLineCreate {
  return { product_id: "", description: "", quantity: 1, unit_price: 0, tax_policy_code: "standard" };
}

export function OrderForm({ onCreated, onCancel }: OrderFormProps) {
  const { items: paymentTerms, loading: termsLoading, error: termsError } = usePaymentTerms();
  const { create, submitting, error } = useCreateOrder();
  const { stockData, stockLoading, checkProductStock } = useStockCheck();

  const [customerId, setCustomerId] = useState("");
  const [paymentTermsCode, setPaymentTermsCode] = useState("NET_30");
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<OrderLineCreate[]>([emptyLine()]);

  // Check stock when product_id changes
  useEffect(() => {
    for (const line of lines) {
      if (line.product_id && line.product_id.length >= 36) {
        checkProductStock(line.product_id);
      }
    }
  }, [lines, checkProductStock]);

  if (termsLoading) return <p aria-busy="true">Loading…</p>;
  if (termsError) return <div role="alert" style={{ color: "#dc2626" }}>{termsError}</div>;

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
    const payload: OrderCreatePayload = {
      customer_id: customerId,
      payment_terms_code: paymentTermsCode as OrderCreatePayload["payment_terms_code"],
      notes: notes || undefined,
      lines: validLines,
    };
    const result = await create(payload);
    if (result) onCreated(result.id);
  };

  return (
    <section aria-label="Create order">
      <h2>New Order</h2>

      {error && (
        <div role="alert" style={{ color: "#dc2626", marginBottom: 12 }}>
          {error}
        </div>
      )}

      <form onSubmit={(e) => void handleSubmit(e)} aria-label="Order form">
        {/* Header fields */}
        <div style={{ display: "flex", gap: 16, marginBottom: 16, flexWrap: "wrap" }}>
          <div>
            <label htmlFor="ord-customer">Customer ID: </label>
            <input
              id="ord-customer"
              type="text"
              required
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              placeholder="Customer UUID"
            />
          </div>

          <div>
            <label htmlFor="ord-terms">Payment terms: </label>
            <select
              id="ord-terms"
              value={paymentTermsCode}
              onChange={(e) => setPaymentTermsCode(e.target.value)}
            >
              {paymentTerms.map((t) => (
                <option key={t.code} value={t.code}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="ord-notes">Notes: </label>
            <input
              id="ord-notes"
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional notes"
            />
          </div>
        </div>

        {/* Line items */}
        <h3>Order Lines</h3>
        <table aria-label="Order line items">
          <thead>
            <tr>
              <th>Product ID</th>
              <th>Description</th>
              <th>Quantity</th>
              <th>Unit Price</th>
              <th>Tax Policy</th>
              <th>Stock</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {lines.map((line, idx) => (
              <tr key={idx}>
                <td>
                  <input
                    type="text"
                    required
                    value={line.product_id}
                    onChange={(e) =>
                      updateLine(idx, { product_id: e.target.value })
                    }
                    placeholder="Product UUID"
                    aria-label={`Line ${idx + 1} product`}
                  />
                </td>
                <td>
                  <input
                    type="text"
                    required
                    value={line.description}
                    onChange={(e) =>
                      updateLine(idx, { description: e.target.value })
                    }
                    placeholder="Description"
                    aria-label={`Line ${idx + 1} description`}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    required
                    min={1}
                    step="any"
                    value={line.quantity}
                    onChange={(e) =>
                      updateLine(idx, { quantity: Number(e.target.value) })
                    }
                    style={{ width: 80 }}
                    aria-label={`Line ${idx + 1} quantity`}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    required
                    min={0}
                    step="0.01"
                    value={line.unit_price}
                    onChange={(e) =>
                      updateLine(idx, { unit_price: Number(e.target.value) })
                    }
                    style={{ width: 100 }}
                    aria-label={`Line ${idx + 1} unit price`}
                  />
                </td>
                <td>
                  <select
                    value={line.tax_policy_code}
                    onChange={(e) =>
                      updateLine(idx, { tax_policy_code: e.target.value })
                    }
                    aria-label={`Line ${idx + 1} tax policy`}
                  >
                    <option value="standard">Standard (5%)</option>
                    <option value="zero">Zero rated</option>
                    <option value="exempt">Exempt</option>
                    <option value="special">Special</option>
                  </select>
                </td>
                <td>
                  {(() => {
                    const pid = line.product_id;
                    if (!pid || pid.length < 36) return null;
                    if (stockLoading[pid]) return <span aria-busy="true">…</span>;
                    const info = stockData[pid];
                    if (!info) return null;
                    const avail = info.total_available;
                    const insufficient = line.quantity > avail;
                    return (
                      <span
                        aria-label={`Line ${idx + 1} stock`}
                        style={{ color: insufficient ? "#dc2626" : "#16a34a", fontWeight: 600 }}
                      >
                        {avail} avail
                        {insufficient && (
                          <span style={{ display: "block", fontSize: "0.8em" }}>
                            Insufficient stock: {avail} units available
                          </span>
                        )}
                      </span>
                    );
                  })()}
                </td>
                <td>
                  {lines.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeLine(idx)}
                      aria-label={`Remove line ${idx + 1}`}
                      style={{ color: "#dc2626" }}
                    >
                      ✕
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <button
          type="button"
          onClick={() => setLines((prev) => [...prev, emptyLine()])}
          style={{ marginTop: 8, marginBottom: 16 }}
        >
          + Add Line
        </button>

        {hasInvalidLines && (
          <p role="alert" style={{ color: "#b45309", marginBottom: 12 }}>
            {lines.length - validLines.length} line(s) incomplete — fill in product ID, description, and quantity (&gt; 0).
          </p>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: 8 }}>
          <button type="submit" disabled={!canSubmit || submitting}>
            {submitting ? "Creating…" : "Create Order"}
          </button>
          <button type="button" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </section>
  );
}
