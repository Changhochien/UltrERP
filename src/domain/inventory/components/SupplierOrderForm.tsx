/** Form to create a new supplier order with dynamic line items. */

import { useState } from "react";
import { useWarehouses } from "../hooks/useWarehouses";
import {
  useSuppliers,
  useCreateSupplierOrder,
} from "../hooks/useSupplierOrders";

interface OrderLine {
  product_id: string;
  warehouse_id: string;
  quantity: number;
  unit_cost: number;
}

interface SupplierOrderFormProps {
  onCreated: (orderId: string) => void;
  onCancel: () => void;
}

function emptyLine(): OrderLine {
  return { product_id: "", warehouse_id: "", quantity: 1, unit_cost: 0 };
}

export function SupplierOrderForm({
  onCreated,
  onCancel,
}: SupplierOrderFormProps) {
  const { suppliers, loading: suppLoading } = useSuppliers();
  const { warehouses, loading: whLoading } = useWarehouses();
  const { create, submitting, error } = useCreateSupplierOrder();

  const [supplierId, setSupplierId] = useState("");
  const [orderDate, setOrderDate] = useState(
    () => new Date().toISOString().slice(0, 10),
  );
  const [expectedArrival, setExpectedArrival] = useState("");
  const [lines, setLines] = useState<OrderLine[]>([emptyLine()]);

  if (suppLoading || whLoading) return <p aria-busy="true">Loading…</p>;

  const updateLine = (idx: number, patch: Partial<OrderLine>) => {
    setLines((prev) =>
      prev.map((l, i) => (i === idx ? { ...l, ...patch } : l)),
    );
  };

  const removeLine = (idx: number) => {
    setLines((prev) => prev.filter((_, i) => i !== idx));
  };

  const validLines = lines.filter(
    (l) => l.product_id && l.warehouse_id && l.quantity > 0,
  );
  const canSubmit = supplierId && orderDate && validLines.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await create({
      supplier_id: supplierId,
      order_date: orderDate,
      expected_arrival_date: expectedArrival || undefined,
      lines: validLines.map((l) => ({
        product_id: l.product_id,
        warehouse_id: l.warehouse_id,
        quantity_ordered: l.quantity,
        unit_cost: l.unit_cost > 0 ? l.unit_cost : undefined,
      })),
    });
    if (result) onCreated(result.id);
  };

  return (
    <section aria-label="Create supplier order">
      <h2>New Supplier Order</h2>

      {error && (
        <div role="alert" style={{ color: "#dc2626", marginBottom: 12 }}>
          {error}
        </div>
      )}

      <form onSubmit={(e) => void handleSubmit(e)} aria-label="Order form">
        {/* Header fields */}
        <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
          <div>
            <label htmlFor="so-supplier">Supplier: </label>
            <select
              id="so-supplier"
              required
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
            >
              <option value="">Select supplier</option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="so-date">Order date: </label>
            <input
              id="so-date"
              type="date"
              required
              value={orderDate}
              onChange={(e) => setOrderDate(e.target.value)}
            />
          </div>

          <div>
            <label htmlFor="so-arrival">Expected arrival: </label>
            <input
              id="so-arrival"
              type="date"
              value={expectedArrival}
              onChange={(e) => setExpectedArrival(e.target.value)}
            />
          </div>
        </div>

        {/* Line items */}
        <h3>Order Lines</h3>
        <table aria-label="Order line items">
          <thead>
            <tr>
              <th>Product ID</th>
              <th>Warehouse</th>
              <th>Quantity</th>
              <th>Unit Cost</th>
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
                  <select
                    required
                    value={line.warehouse_id}
                    onChange={(e) =>
                      updateLine(idx, { warehouse_id: e.target.value })
                    }
                    aria-label={`Line ${idx + 1} warehouse`}
                  >
                    <option value="">Select</option>
                    {warehouses.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <input
                    type="number"
                    required
                    min={1}
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
                    min={0}
                    step="0.01"
                    value={line.unit_cost}
                    onChange={(e) =>
                      updateLine(idx, { unit_cost: Number(e.target.value) })
                    }
                    style={{ width: 100 }}
                    aria-label={`Line ${idx + 1} unit cost`}
                  />
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
