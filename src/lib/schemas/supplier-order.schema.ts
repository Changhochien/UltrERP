import { z } from "zod";

import type {
  CreateSupplierOrderRequest,
  ProductSupplierInfo,
} from "../../domain/inventory/types";

export interface SupplierOrderLineFormValues {
  product_id: string;
  warehouse_id: string;
  quantity: number;
  unit_cost: string;
}

const integerFromInput = (value: unknown) => {
  if (value === "" || value === null || value === undefined) {
    return 0;
  }

  const parsed = Number(value);
  return Number.isNaN(parsed) ? Number.NaN : parsed;
};

export const supplierOrderLineFormSchema = z.object({
  product_id: z.string().trim().min(1, "Product is required"),
  warehouse_id: z.string().trim().min(1, "Warehouse is required"),
  quantity: z.number().int("Quantity must be a whole number").gt(0, "Quantity must be greater than zero"),
  unit_cost: z.string().superRefine((value, ctx) => {
    const normalized = value.trim();

    if (!normalized) {
      return;
    }

    const parsed = Number(normalized);
    if (!Number.isFinite(parsed) || parsed < 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Unit cost must be zero or greater",
      });
    }
  }),
});

export const supplierOrderFormSchema = z.object({
  supplier_id: z.string().trim().min(1, "Supplier is required"),
  order_date: z.string().trim().min(1, "Order date is required"),
  expected_arrival_date: z.string().trim(),
  lines: z.array(supplierOrderLineFormSchema).min(1, "Add at least one line"),
});

export type SupplierOrderFormValues = z.infer<typeof supplierOrderFormSchema>;

export const supplierOrderNumberFieldOptions = {
  setValueAs: integerFromInput,
};

export function emptySupplierOrderLine(): SupplierOrderLineFormValues {
  return { product_id: "", warehouse_id: "", quantity: 1, unit_cost: "" };
}

export function hydrateSupplierOrderLine(line: {
  product_id: string;
  warehouse_id: string;
  quantity: number;
  unit_cost?: string;
}): SupplierOrderLineFormValues {
  return {
    product_id: line.product_id,
    warehouse_id: line.warehouse_id,
    quantity: line.quantity,
    unit_cost: line.unit_cost ?? "",
  };
}

export function buildSupplierOrderFormValues(options: {
  initialSupplierId?: string;
  initialOrderDate: string;
  initialExpectedArrivalDate?: string;
  initialLines?: Array<{
    product_id: string;
    warehouse_id: string;
    quantity: number;
    unit_cost?: string;
  }>;
}): SupplierOrderFormValues {
  return {
    supplier_id: options.initialSupplierId ?? "",
    order_date: options.initialOrderDate,
    expected_arrival_date: options.initialExpectedArrivalDate ?? "",
    lines:
      options.initialLines && options.initialLines.length > 0
        ? options.initialLines.map(hydrateSupplierOrderLine)
        : [emptySupplierOrderLine()],
  };
}

export function toSupplierOrderCreatePayload(
  values: SupplierOrderFormValues,
): CreateSupplierOrderRequest {
  return {
    supplier_id: values.supplier_id.trim(),
    order_date: values.order_date.trim(),
    expected_arrival_date: values.expected_arrival_date.trim() || undefined,
    lines: values.lines.map((line) => {
      const normalizedUnitCost = line.unit_cost.trim();

      return {
        product_id: line.product_id.trim(),
        warehouse_id: line.warehouse_id.trim(),
        quantity_ordered: Number(line.quantity),
        unit_price: normalizedUnitCost === "" ? undefined : Number(normalizedUnitCost),
      };
    }),
  };
}

export function normalizeResolvedSupplier(
  results: Array<{ ok: true; data: ProductSupplierInfo | null } | { ok: false; error: string }>,
  selectedProductIds: string[],
): { supplierId: string | null; message: string | null } {
  const resolvedSuppliers = results
    .filter((result): result is { ok: true; data: ProductSupplierInfo } => result.ok && result.data != null)
    .map((result) => result.data);
  const uniqueSupplierIds = Array.from(new Set(resolvedSuppliers.map((supplier) => supplier.supplier_id)));
  const hasMissingSupplier = results.some((result) => !result.ok || (result.ok && result.data == null));

  if (!hasMissingSupplier && uniqueSupplierIds.length === 1) {
    return { supplierId: uniqueSupplierIds[0], message: null };
  }

  if (uniqueSupplierIds.length > 1) {
    return {
      supplierId: null,
      message: "Selected products have different default suppliers. Choose one manually.",
    };
  }

  if (selectedProductIds.length > 1 && hasMissingSupplier) {
    return {
      supplierId: null,
      message: "Selected products do not resolve to one supplier. Choose one manually.",
    };
  }

  return { supplierId: null, message: null };
}