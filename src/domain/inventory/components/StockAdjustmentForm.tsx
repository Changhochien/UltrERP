/** Stock adjustment form for recording inventory changes with reason codes. */

import { useState } from "react";

import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../../components/ui/dialog";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
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
    <section aria-label="Stock adjustment form" className="space-y-5">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold tracking-tight">Record Stock Adjustment</h2>
        <p className="text-sm text-muted-foreground">Post manual stock movements with warehouse and reason-code control.</p>
      </div>

      {error ? <SurfaceMessage tone="danger">{error}</SurfaceMessage> : null}
      {result ? (
        <SurfaceMessage tone="success" role="status">
          Adjustment recorded. Updated stock: {result.updated_stock} units.
        </SurfaceMessage>
      ) : null}

      <SectionCard title="Adjustment Form" description="Enter the product, warehouse, quantity delta, and reason code for the stock change.">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setShowConfirm(true);
          }}
          aria-label="Adjustment form"
          className="grid gap-4"
        >
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span>Product ID</span>
              <Input
                id="adj-product"
                type="text"
                required
                value={productId}
                onChange={(e) => setProductId(e.target.value)}
                placeholder="Enter product UUID"
              />
            </label>

            <label className="space-y-2">
              <span>Warehouse</span>
              <select
                id="adj-warehouse"
                required
                value={warehouseId}
                onChange={(e) => setWarehouseId(e.target.value)}
              >
                <option value="">Select warehouse</option>
                {warehouses.map((warehouse) => (
                  <option key={warehouse.id} value={warehouse.id}>
                    {warehouse.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span>Quantity change</span>
              <Input
                id="adj-quantity"
                type="number"
                required
                value={quantityChange}
                onChange={(e) => setQuantityChange(Number(e.target.value))}
                aria-describedby="qty-hint"
              />
              <small id="qty-hint" className="text-sm text-muted-foreground">
                Positive to add, negative to remove
              </small>
            </label>

            <label className="space-y-2">
              <span>Reason code</span>
              <select
                id="adj-reason"
                required
                value={reasonCode}
                onChange={(e) => setReasonCode(e.target.value)}
              >
                <option value="">Select reason</option>
                {codes.map((reason) => (
                  <option key={reason.value} value={reason.value}>
                    {reason.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="space-y-2">
            <span>Notes (optional)</span>
            <textarea
              id="adj-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={1000}
              rows={3}
            />
          </label>

          <div>
            <Button type="submit" disabled={!canSubmit || submitting}>
              {submitting ? "Submitting…" : "Record Adjustment"}
            </Button>
          </div>
        </form>
      </SectionCard>

      <Dialog open={showConfirm} onOpenChange={setShowConfirm}>
        <DialogContent aria-label="Confirm adjustment">
          <DialogHeader>
            <DialogTitle>Confirm adjustment</DialogTitle>
            <DialogDescription>
              Confirm adjustment of <strong>{quantityChange > 0 ? "+" : ""}{quantityChange}</strong> units ({reasonCode}).
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setShowConfirm(false)}>
              Cancel
            </Button>
            <Button type="button" onClick={() => void handleSubmit()} disabled={submitting}>
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
