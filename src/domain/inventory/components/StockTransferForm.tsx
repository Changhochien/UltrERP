/** Stock transfer form for inter-warehouse transfers. */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { ProductCombobox } from "@/components/products/ProductCombobox";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { createTransfer } from "@/lib/api/inventory";

import { useWarehouses } from "../hooks/useWarehouses";
import type { TransferResponse } from "../types";

interface StockTransferFormProps {
  defaultProductId?: string;
  defaultFromWarehouseId?: string;
  onSuccess?: (transfer: TransferResponse) => void;
  onCancel?: () => void;
}

export function StockTransferForm({
  defaultProductId = "",
  defaultFromWarehouseId = "",
  onSuccess,
  onCancel,
}: StockTransferFormProps) {
  const { t } = useTranslation("common", { keyPrefix: "inventory.transferForm" });
  const { warehouses, loading, error: warehousesError } = useWarehouses();
  const [fromId, setFromId] = useState(defaultFromWarehouseId);
  const [toId, setToId] = useState("");
  const [productId, setProductId] = useState(defaultProductId);
  const [quantity, setQuantity] = useState(1);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);

  const quantityError = quantity > 0 && !Number.isInteger(quantity)
    ? t("quantityInteger")
    : null;

  const canSubmit =
    fromId && toId && productId && quantity > 0 && fromId !== toId && !quantityError;

  const fromWarehouse = useMemo(
    () => warehouses.find((warehouse) => warehouse.id === fromId),
    [fromId, warehouses],
  );
  const toWarehouse = useMemo(
    () => warehouses.find((warehouse) => warehouse.id === toId),
    [toId, warehouses],
  );

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
        setResult(
          t("success", {
            transferId: resp.data.id,
            quantity,
            fromWarehouse: fromWarehouse?.name ?? t("unknownWarehouse"),
            toWarehouse: toWarehouse?.name ?? t("unknownWarehouse"),
          }),
        );
        setProductId(defaultProductId);
        setFromId(defaultFromWarehouseId);
        setToId("");
        setQuantity(1);
        setNotes("");
        onSuccess?.(resp.data);
      } else {
        setError(resp.error);
      }
    } catch {
      setError(t("networkError"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (canSubmit) {
            setShowConfirm(true);
          }
        }}
      >
        {loading ? <p className="text-sm text-muted-foreground">{t("loadingWarehouses")}</p> : null}
        {warehousesError ? <p className="text-sm text-destructive">{warehousesError}</p> : null}
        {result ? <p className="text-sm text-emerald-700">{result}</p> : null}
        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label htmlFor="transfer-from-warehouse" className="block text-sm font-medium">
              {t("fromWarehouse")}
            </label>
            <select
              id="transfer-from-warehouse"
              className="flex h-10 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm"
              value={fromId}
              onChange={(event) => setFromId(event.target.value)}
              disabled={loading || submitting}
            >
              <option value="">{t("selectWarehouse")}</option>
              {warehouses.map((warehouse) => (
                <option key={warehouse.id} value={warehouse.id}>
                  {warehouse.name} ({warehouse.code})
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label htmlFor="transfer-to-warehouse" className="block text-sm font-medium">
              {t("toWarehouse")}
            </label>
            <select
              id="transfer-to-warehouse"
              className="flex h-10 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm"
              value={toId}
              onChange={(event) => setToId(event.target.value)}
              disabled={loading || submitting}
            >
              <option value="">{t("selectWarehouse")}</option>
              {warehouses
                .filter((warehouse) => warehouse.id !== fromId)
                .map((warehouse) => (
                  <option key={warehouse.id} value={warehouse.id}>
                    {warehouse.name} ({warehouse.code})
                  </option>
                ))}
            </select>
          </div>
        </div>

        <div className="space-y-2">
          <label id="transfer-product-label" className="block text-sm font-medium">
            {t("product")}
          </label>
          <ProductCombobox
            value={productId}
            onChange={setProductId}
            onClear={() => setProductId("")}
            placeholder={t("productPlaceholder")}
            disabled={submitting}
            ariaLabelledBy="transfer-product-label"
          />
        </div>

        <div className="grid gap-4 md:grid-cols-[180px_minmax(0,1fr)]">
          <div className="space-y-2">
            <label htmlFor="transfer-quantity" className="block text-sm font-medium">
              {t("quantity")}
            </label>
            <Input
              id="transfer-quantity"
              type="number"
              min={1}
              step={1}
              value={quantity}
              onChange={(event) => {
                const nextValue = Number(event.target.value);
                setQuantity(Number.isFinite(nextValue) ? nextValue : 0);
              }}
              disabled={submitting}
            />
            {quantityError ? <p className="text-sm text-destructive">{quantityError}</p> : null}
          </div>

          <div className="space-y-2">
            <label htmlFor="transfer-notes" className="block text-sm font-medium">
              {t("notes")}
            </label>
            <Textarea
              id="transfer-notes"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder={t("notesPlaceholder")}
              disabled={submitting}
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={!canSubmit || submitting || loading}>
            {submitting ? t("submitting") : t("submit")}
          </Button>
          {onCancel ? (
            <Button type="button" variant="outline" onClick={onCancel} disabled={submitting}>
              {t("cancel")}
            </Button>
          ) : null}
        </div>
      </form>

      <Dialog open={showConfirm} onOpenChange={setShowConfirm}>
        <DialogContent aria-label={t("confirmTitle")} className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{t("confirmTitle")}</DialogTitle>
            <DialogDescription>
              {t("confirmDescription", {
                quantity,
                fromWarehouse: fromWarehouse?.name ?? t("unknownWarehouse"),
                toWarehouse: toWarehouse?.name ?? t("unknownWarehouse"),
              })}
            </DialogDescription>
          </DialogHeader>
          <div className="flex gap-2">
            <Button type="button" onClick={() => void handleSubmit()} disabled={submitting}>
              {t("confirm")}
            </Button>
            <Button type="button" variant="outline" onClick={() => setShowConfirm(false)} disabled={submitting}>
              {t("cancel")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
