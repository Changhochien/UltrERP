/** Stock adjustment form for recording inventory changes with reason codes. */

import { useState } from "react";
import { useWarehouses } from "../hooks/useWarehouses";
import {
  useReasonCodes,
  useStockAdjustment,
} from "../hooks/useStockAdjustment";

export function StockAdjustmentForm() {
  const { warehouses, loading: whLoading } = useWarehouses();
  const { codes, loading: codesLoading } = useReasonCodes();
  const { submit, submitting, result, error, clearError } =
    useStockAdjustment();

  const [productId, setProductId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [quantityChange, setQuantityChange] = useState(0);
  const [reasonCode, setReasonCode] = useState("");
  const [notes, setNotes] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);

  if (whLoading || codesLoading) return <p aria-busy="true">Loading…</p>;

  const canSubmit =
    productId && warehouseId && quantityChange !== 0 && reasonCode;

  const handleSubmit = async () => {
    setShowConfirm(false);
    clearError();
    const data = await submit({
      product_id: productId,
      warehouse_id: warehouseId,
      quantity_change: quantityChange,
      reason_code: reasonCode,
      notes: notes || undefined,
    });
    if (data) {
      setProductId("");
      setQuantityChange(0);
      setNotes("");
    }
  };

  return (
    <section aria-label="Stock adjustment form">
      <h2>Record Stock Adjustment</h2>

      {error && (
        <div role="alert" style={{ color: "#dc2626", marginBottom: 12 }}>
          {error}
        </div>
      )}

      {result && (
        <div role="status" style={{ color: "#16a34a", marginBottom: 12 }}>
          Adjustment recorded. Updated stock: {result.updated_stock} units.
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setShowConfirm(true);
        }}
        aria-label="Adjustment form"
      >
        <div style={{ marginBottom: 8 }}>
          <label htmlFor="adj-product">Product ID: </label>
          <input
            id="adj-product"
            type="text"
            required
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            placeholder="Enter product UUID"
          />
        </div>

        <div style={{ marginBottom: 8 }}>
          <label htmlFor="adj-warehouse">Warehouse: </label>
          <select
            id="adj-warehouse"
            required
            value={warehouseId}
            onChange={(e) => setWarehouseId(e.target.value)}
          >
            <option value="">Select warehouse</option>
            {warehouses.map((wh) => (
              <option key={wh.id} value={wh.id}>
                {wh.name}
              </option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: 8 }}>
          <label htmlFor="adj-quantity">Quantity change: </label>
          <input
            id="adj-quantity"
            type="number"
            required
            value={quantityChange}
            onChange={(e) => setQuantityChange(Number(e.target.value))}
            aria-describedby="qty-hint"
          />
          <small id="qty-hint" style={{ display: "block", color: "#6b7280" }}>
            Positive to add, negative to remove
          </small>
        </div>

        <div style={{ marginBottom: 8 }}>
          <label htmlFor="adj-reason">Reason code: </label>
          <select
            id="adj-reason"
            required
            value={reasonCode}
            onChange={(e) => setReasonCode(e.target.value)}
          >
            <option value="">Select reason</option>
            {codes.map((rc) => (
              <option key={rc.value} value={rc.value}>
                {rc.label}
              </option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: 8 }}>
          <label htmlFor="adj-notes">Notes (optional): </label>
          <textarea
            id="adj-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            maxLength={1000}
            rows={2}
          />
        </div>

        <button type="submit" disabled={!canSubmit || submitting}>
          {submitting ? "Submitting…" : "Record Adjustment"}
        </button>
      </form>

      {showConfirm && (
        <div
          role="dialog"
          aria-label="Confirm adjustment"
          aria-modal="true"
          style={{
            position: "fixed",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "rgba(0,0,0,0.5)",
          }}
        >
          <div
            style={{
              background: "#fff",
              padding: 24,
              borderRadius: 8,
              maxWidth: 400,
            }}
          >
            <p>
              Confirm adjustment of{" "}
              <strong>
                {quantityChange > 0 ? "+" : ""}
                {quantityChange}
              </strong>{" "}
              units ({reasonCode})?
            </p>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button
                type="button"
                onClick={() => setShowConfirm(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void handleSubmit()}
                disabled={submitting}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
