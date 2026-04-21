import { z } from "zod";

import type { ProductUpdate } from "../../domain/inventory/types";

export const productFormSchema = z.object({
  code: z.string().trim().min(1, "Code is required").max(100, "Code must be 100 characters or fewer"),
  name: z.string().trim().min(1, "Name is required").max(500, "Name must be 500 characters or fewer"),
  category_id: z.string().trim().nullable(),
  category_name: z.string(),
  description: z.string(),
  unit: z.string().trim().min(1, "Unit is required").max(50, "Unit must be 50 characters or fewer"),
  standard_cost: z
    .string()
    .superRefine((value, ctx) => {
      const normalized = value.trim();

      if (!normalized) {
        return;
      }

      const parsed = Number(normalized);
      if (!Number.isFinite(parsed)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Standard cost must be a valid number",
        });
      } else if (parsed < 0) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Standard cost must be greater than or equal to 0",
        });
      }
    }),
});

export type ProductFormValues = z.infer<typeof productFormSchema>;

export const defaultProductFormValues: ProductFormValues = {
  code: "",
  name: "",
  category_id: null,
  category_name: "",
  description: "",
  unit: "pcs",
  standard_cost: "",
};

export function toProductUpdatePayload(values: ProductFormValues): ProductUpdate {
  const normalizedStandardCost = values.standard_cost.trim();

  return {
    code: values.code.trim(),
    name: values.name.trim(),
    category_id: values.category_id,
    description: values.description.trim(),
    unit: values.unit.trim(),
    standard_cost: normalizedStandardCost ? normalizedStandardCost : null,
  };
}