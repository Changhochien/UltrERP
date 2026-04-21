/** Stock adjustment form for recording inventory changes with reason codes. */

import { useState } from "react";
import { useTranslation } from "react-i18next";

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
import { ProductCombobox } from "../../../components/products/ProductCombobox";
import { collectIssueMessages } from "../../../lib/collectFormErrorMessages";
import {
  stockAdjustmentFormSchema,
  toStockAdjustmentPayload,
} from "../../../lib/schemas/stock-adjustment.schema";
import { useProductDetail } from "../hooks/useProductDetail";
import { useWarehouses } from "../hooks/useWarehouses";
import {
  useReasonCodes,
  useStockAdjustment,
} from "../hooks/useStockAdjustment";

interface StockAdjustmentFormProps {
  defaultProductId?: string;
  defaultWarehouseId?: string;
  confirmBeforeSubmit?: boolean;
}

export function StockAdjustmentForm({
  defaultProductId = "",
  defaultWarehouseId = "",
  confirmBeforeSubmit = true,
}: StockAdjustmentFormProps) {
  const { t } = useTranslation("common", { keyPrefix: "inventory.stockAdjustmentForm" });
  const { warehouses, loading: whLoading } = useWarehouses();
  const { codes, loading: codesLoading } = useReasonCodes();
  const { submit, submitting, result, error, clearError } =
    useStockAdjustment();

  const [productId, setProductId] = useState(defaultProductId);
  const { product } = useProductDetail(productId || null);
  const [warehouseId, setWarehouseId] = useState(defaultWarehouseId);
  const [quantityChange, setQuantityChange] = useState(0);
  const [reasonCode, setReasonCode] = useState("");
  const [notes, setNotes] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);
  const [validationMessages, setValidationMessages] = useState<string[]>([]);

  if (whLoading || codesLoading) return <p aria-busy="true">{t("loading")}</p>;

  const canSubmit =
    productId && warehouseId && quantityChange !== 0 && reasonCode;
  const selectedReasonLabel = codes.find((reason) => reason.value === reasonCode)?.label ?? reasonCode;

  const parseForm = () =>
    stockAdjustmentFormSchema.safeParse({
      product_id: productId,
      warehouse_id: warehouseId,
      quantity_change: Number(quantityChange),
      reason_code: reasonCode,
      notes,
    });

  const handleRequestSubmit = () => {
    const parsed = parseForm();
    if (!parsed.success) {
      setValidationMessages(collectIssueMessages(parsed.error.issues));
      setShowConfirm(false);
      return;
    }

    setValidationMessages([]);
    if (!confirmBeforeSubmit) {
      void handleSubmit();
      return;
    }

    setShowConfirm(true);
  };

  const handleSubmit = async () => {
    setShowConfirm(false);
    clearError();
    const parsed = parseForm();
    if (!parsed.success) {
      setValidationMessages(collectIssueMessages(parsed.error.issues));
      return;
    }

    setValidationMessages([]);
    const data = await submit(toStockAdjustmentPayload(parsed.data));
    if (data) {
      setProductId("");
      setQuantityChange(0);
      setNotes("");
    }
  };

  return (
    <section aria-label={t("title")} className="space-y-5">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold tracking-tight">{t("title")}</h2>
        <p className="text-sm text-muted-foreground">{t("description")}</p>
      </div>

      {error ? <SurfaceMessage tone="danger">{error}</SurfaceMessage> : null}
      {validationMessages.length > 0 ? (
        <SurfaceMessage tone="warning" role="alert">
          <div className="space-y-1">
            {validationMessages.map((message) => (
              <p key={message}>{message}</p>
            ))}
          </div>
        </SurfaceMessage>
      ) : null}
      {result ? (
        <SurfaceMessage tone="success" role="status">
          {t("success", { count: result.updated_stock })}
        </SurfaceMessage>
      ) : null}

      <SectionCard title={t("sectionTitle")} description={t("sectionDescription")}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleRequestSubmit();
          }}
          aria-label="Adjustment form"
          className="grid gap-4"
        >
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span>{t("productLabel")}</span>
              <ProductCombobox
                value={productId}
                onChange={setProductId}
                placeholder={t("productPlaceholder")}
              />
              {product && (
                <span className="text-sm font-medium text-foreground">
                  {product.name}
                </span>
              )}
            </label>

            <label className="space-y-2" htmlFor="adj-warehouse">
              <span>{t("warehouseLabel")}</span>
              <select
                id="adj-warehouse"
                required
                value={warehouseId}
                onChange={(e) => setWarehouseId(e.target.value)}
              >
                <option value="">{t("warehousePlaceholder")}</option>
                {warehouses.map((warehouse) => (
                  <option key={warehouse.id} value={warehouse.id}>
                    {warehouse.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2" htmlFor="adj-quantity">
              <span>{t("quantityChangeLabel")}</span>
              <Input
                id="adj-quantity"
                type="number"
                required
                value={quantityChange}
                onChange={(e) => setQuantityChange(Number(e.target.value))}
                aria-describedby="qty-hint"
              />
              <small id="qty-hint" className="text-sm text-muted-foreground">
                {t("quantityHint")}
              </small>
            </label>

            <label className="space-y-2" htmlFor="adj-reason">
              <span>{t("reasonCodeLabel")}</span>
              <select
                id="adj-reason"
                required
                value={reasonCode}
                onChange={(e) => setReasonCode(e.target.value)}
              >
                <option value="">{t("reasonCodePlaceholder")}</option>
                {codes.map((reason) => (
                  <option key={reason.value} value={reason.value}>
                    {reason.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="space-y-2" htmlFor="adj-notes">
            <span>{t("notesLabel")}</span>
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
              {submitting ? t("submittingLabel") : t("submitLabel")}
            </Button>
          </div>
        </form>
      </SectionCard>

      <Dialog open={showConfirm} onOpenChange={setShowConfirm}>
        <DialogContent aria-label={t("confirmTitle")}>
          <DialogHeader>
            <DialogTitle>{t("confirmTitle")}</DialogTitle>
            <DialogDescription>
              {t("confirmDescription", {
                quantity: `${quantityChange > 0 ? "+" : ""}${quantityChange}`,
                reason: selectedReasonLabel,
              })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setShowConfirm(false)}>
              {t("cancel")}
            </Button>
            <Button type="button" onClick={() => void handleSubmit()} disabled={submitting}>
              {t("confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
