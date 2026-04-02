/** Stock transfer form for inter-warehouse transfers. */

import { useState } from "react";
import { useWarehouses } from "../hooks/useWarehouses";
import { createTransfer } from "../../../lib/api/inventory";

export function StockTransferForm() {
  const { warehouses, loading } = useWarehouses();
  const [fromId, setFromId] = useState("");
  const [toId, setToId] = useState("");
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);

  if (loading) return <p>Loading warehouses…</p>;

  const canSubmit =
    fromId && toId && productId && quantity > 0 && fromId !== toId;

  const handleSubmit = async () => {
    setShowConfirm(false);
    setSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const resp = await createTransfer({
        from_warehouse_id: fromId,
        to_warehouse_id: toId,
        product_id: productId,
        quantity,
        notes: notes || undefined,
      });

      if (resp.ok) {
        setResult(`Transfer ${resp.data.id} completed successfully.`);
        setProductId("");
        setQuantity(1);
        setNotes("");
      } else {
        setError(resp.error.detail);
      }
    } catch {
      setError("Network error — please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const fromWarehouse = warehouses.find((w) => w.id === fromId);
  const toWarehouse = warehouses.find((w) => w.id === toId);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        setShowConfirm(true);
      }}
    >
      <h2>Stock Transfer</h2>

      <label>
        From Warehouse
        <select value={fromId} onChange={(e) => setFromId(e.target.value)}>
          <option value="">Select…</option>
          {warehouses.map((wh) => (
            <option key={wh.id} value={wh.id}>
              {wh.name} ({wh.code})
            </option>
          ))}
        </select>
      </label>

      <label>
        To Warehouse
        <select value={toId} onChange={(e) => setToId(e.target.value)}>
          <option value="">Select…</option>
          {warehouses
            .filter((wh) => wh.id !== fromId)
            .map((wh) => (
              <option key={wh.id} value={wh.id}>
                {wh.name} ({wh.code})
              </option>
            ))}
        </select>
      </label>

      <label>
        Product ID
        <input
          type="text"
          value={productId}
          onChange={(e) => setProductId(e.target.value)}
          placeholder="Product UUID"
        />
      </label>

      <label>
        Quantity
        <input
          type="number"
          min={1}
          value={quantity}
          onChange={(e) => setQuantity(Number(e.target.value))}
        />
      </label>

      <label>
        Notes (optional)
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
      </label>

      <button type="submit" disabled={!canSubmit || submitting}>
        {submitting ? "Transferring…" : "Transfer Stock"}
      </button>

      {showConfirm && (
        <dialog open>
          <p>
            Transfer {quantity} unit(s) from{" "}
            <strong>{fromWarehouse?.name}</strong> to{" "}
            <strong>{toWarehouse?.name}</strong>?
          </p>
          <button type="button" onClick={handleSubmit}>
            Confirm
          </button>
          <button type="button" onClick={() => setShowConfirm(false)}>
            Cancel
          </button>
        </dialog>
      )}

      {result && <p className="success">{result}</p>}
      {error && <p className="error">{error}</p>}
    </form>
  );
}
