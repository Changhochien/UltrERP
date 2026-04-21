import { z } from "zod";

import type { StockAdjustmentRequest } from "../../domain/inventory/types";

const integerFromInput = (value: unknown) => {
  if (value === "" || value === null || value === undefined) {
    return 0;
  }

  const parsed = Number(value);
  return Number.isNaN(parsed) ? Number.NaN : parsed;
};

export const stockAdjustmentFormSchema = z.object({
  product_id: z.string().trim().min(1, "Product is required"),
  warehouse_id: z.string().trim().min(1, "Warehouse is required"),
  quantity_change: z
    .number()
    .int("Quantity change must be a whole number")
    .refine((value) => value !== 0, "Quantity change cannot be zero"),
  reason_code: z.string().trim().min(1, "Reason code is required"),
  notes: z.string().max(1000, "Notes must be 1000 characters or fewer"),
});

export type StockAdjustmentFormValues = z.infer<typeof stockAdjustmentFormSchema>;

export const stockAdjustmentNumberFieldOptions = {
  setValueAs: integerFromInput,
};

export function buildStockAdjustmentFormValues(
  defaultProductId = "",
  defaultWarehouseId = "",
): StockAdjustmentFormValues {
  return {
    product_id: defaultProductId,
    warehouse_id: defaultWarehouseId,
    quantity_change: 0,
    reason_code: "",
    notes: "",
  };
}

export function toStockAdjustmentPayload(
  values: StockAdjustmentFormValues,
): StockAdjustmentRequest {
  const normalizedNotes = values.notes.trim();

  return {
    product_id: values.product_id.trim(),
    warehouse_id: values.warehouse_id.trim(),
    quantity_change: Number(values.quantity_change),
    reason_code: values.reason_code.trim(),
    notes: normalizedNotes || undefined,
  };
}