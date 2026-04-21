import { useEffect, useState } from "react";

import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Spinner } from "../../../components/ui/Spinner";
import { Textarea } from "../../../components/ui/textarea";
import {
  defaultProductFormValues,
  productFormSchema,
  toProductUpdatePayload,
  type ProductFormValues,
} from "../../../lib/schemas/product.schema";
import { CategoryCombobox } from "./CategoryCombobox";
import { UnitCombobox } from "./UnitCombobox";
import type { ProductResponse, ProductUpdate } from "../types";

export interface ProductFormFieldError {
  field: string;
  message: string;
}

export type ProductFormSubmitResult =
  | { ok: true; product: ProductResponse }
  | { ok: false; fieldErrors?: ProductFormFieldError[]; formError?: string };

export interface ProductFormLabels {
  code: string;
  name: string;
  category: string;
  categoryPlaceholder: string;
  description: string;
  unit: string;
  unitPlaceholder: string;
  standardCost: string;
  cancel: string;
}

const DEFAULT_LABELS: ProductFormLabels = {
  code: "Code",
  name: "Name",
  category: "Category",
  categoryPlaceholder: "Search or create category...",
  description: "Description",
  unit: "Unit",
  unitPlaceholder: "Search unit...",
  standardCost: "Standard Cost",
  cancel: "Cancel",
};

interface ProductFormProps {
  initialValues?: Partial<ProductFormValues>;
  onSubmit: (values: ProductUpdate) => Promise<ProductFormSubmitResult>;
  onSuccess: (product: ProductResponse) => void;
  onCancel?: () => void;
  submitLabel: string;
  submittingLabel: string;
  labels?: Partial<ProductFormLabels>;
}

function toErrorMap(errors: ProductFormFieldError[]): Record<string, string> {
  return errors.reduce<Record<string, string>>((acc, error) => {
    if (error.field) {
      acc[error.field] = error.message;
    }
    return acc;
  }, {});
}

function toIssueErrorMap(
  issues: Array<{ path: Array<string | number>; message: string }>,
): Record<string, string> {
  return issues.reduce<Record<string, string>>((acc, issue) => {
    const field = typeof issue.path[0] === "string" ? issue.path[0] : "";
    if (field && !acc[field]) {
      acc[field] = issue.message;
    }
    return acc;
  }, {});
}

export function ProductForm({
  initialValues,
  onSubmit,
  onSuccess,
  onCancel,
  submitLabel,
  submittingLabel,
  labels,
}: ProductFormProps) {
  const fieldLabels = { ...DEFAULT_LABELS, ...labels };
  const [formData, setFormData] = useState<ProductFormValues>(defaultProductFormValues);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setFormData({
      code: initialValues?.code ?? defaultProductFormValues.code,
      name: initialValues?.name ?? defaultProductFormValues.name,
      category_id: initialValues?.category_id ?? defaultProductFormValues.category_id,
      category_name: initialValues?.category_name ?? defaultProductFormValues.category_name,
      description: initialValues?.description ?? defaultProductFormValues.description,
      unit: initialValues?.unit ?? defaultProductFormValues.unit,
      standard_cost: initialValues?.standard_cost ?? defaultProductFormValues.standard_cost,
    });
    setErrors({});
    setServerError(null);
  }, [
    initialValues?.category_id,
    initialValues?.category_name,
    initialValues?.code,
    initialValues?.description,
    initialValues?.name,
    initialValues?.standard_cost,
    initialValues?.unit,
  ]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setServerError(null);

    const parsedValues = productFormSchema.safeParse(formData);
    if (!parsedValues.success) {
      setErrors(toIssueErrorMap(parsedValues.error.issues));
      setServerError(
        parsedValues.error.issues.find((issue) => issue.path.length === 0)?.message ?? null,
      );
      return;
    }

    setErrors({});
    setIsSubmitting(true);
    try {
      const result = await onSubmit(toProductUpdatePayload(parsedValues.data));

      if (result.ok) {
        onSuccess(result.product);
        return;
      }

      setErrors(toErrorMap(result.fieldErrors ?? []));
      const generalError = result.fieldErrors?.find((error) => !error.field)?.message ?? null;
      setServerError(result.formError ?? generalError);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {serverError && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {serverError}
        </div>
      )}

      <div>
        <label htmlFor="product-code" className="block text-sm font-medium">
          {fieldLabels.code} <span className="text-destructive">*</span>
        </label>
        <Input
          id="product-code"
          type="text"
          value={formData.code}
          onChange={(event) => setFormData((current) => ({ ...current, code: event.target.value }))}
          aria-invalid={Boolean(errors.code)}
          disabled={isSubmitting}
        />
        {errors.code && <p className="mt-1 text-sm text-destructive">{errors.code}</p>}
      </div>

      <div>
        <label htmlFor="product-name" className="block text-sm font-medium">
          {fieldLabels.name} <span className="text-destructive">*</span>
        </label>
        <Input
          id="product-name"
          type="text"
          value={formData.name}
          onChange={(event) => setFormData((current) => ({ ...current, name: event.target.value }))}
          aria-invalid={Boolean(errors.name)}
          disabled={isSubmitting}
        />
        {errors.name && <p className="mt-1 text-sm text-destructive">{errors.name}</p>}
      </div>

      <div>
        <label id="product-category-label" className="block text-sm font-medium">
          {fieldLabels.category}
        </label>
        <div id="product-category" className="mt-1">
          <CategoryCombobox
            inputId="product-category-trigger"
            ariaLabelledBy="product-category-label"
            value={formData.category_id}
            valueLabel={formData.category_name}
            onChange={(category_id, category_name) =>
              setFormData((current) => ({ ...current, category_id, category_name }))
            }
            onClear={() => setFormData((current) => ({ ...current, category_id: null, category_name: "" }))}
            placeholder={fieldLabels.categoryPlaceholder}
            allowCreate
            disabled={isSubmitting}
          />
        </div>
        {errors.category && <p className="mt-1 text-sm text-destructive">{errors.category}</p>}
      </div>

      <div>
        <label htmlFor="product-description" className="block text-sm font-medium">
          {fieldLabels.description}
        </label>
        <Textarea
          id="product-description"
          value={formData.description}
          onChange={(event) => setFormData((current) => ({ ...current, description: event.target.value }))}
          rows={4}
          disabled={isSubmitting}
        />
      </div>

      <div>
        <label id="product-unit-label" className="block text-sm font-medium">
          {fieldLabels.unit} <span className="text-destructive">*</span>
        </label>
        <div id="product-unit" className="mt-1">
          <UnitCombobox
            inputId="product-unit-trigger"
            ariaLabelledBy="product-unit-label"
            value={formData.unit}
            onChange={(unit) => setFormData((current) => ({ ...current, unit }))}
            onClear={() => setFormData((current) => ({ ...current, unit: "" }))}
            placeholder={fieldLabels.unitPlaceholder}
            disabled={isSubmitting}
          />
        </div>
        {errors.unit && <p className="mt-1 text-sm text-destructive">{errors.unit}</p>}
      </div>

      <div>
        <label htmlFor="product-standard-cost" className="block text-sm font-medium">
          {fieldLabels.standardCost}
        </label>
        <Input
          id="product-standard-cost"
          type="text"
          inputMode="decimal"
          value={formData.standard_cost}
          onChange={(event) => setFormData((current) => ({ ...current, standard_cost: event.target.value }))}
          aria-invalid={Boolean(errors.standard_cost)}
          disabled={isSubmitting}
        />
        {errors.standard_cost && <p className="mt-1 text-sm text-destructive">{errors.standard_cost}</p>}
      </div>

      <div className="flex gap-2">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Spinner size="sm" className="text-current" />
              {submittingLabel}
            </>
          ) : (
            submitLabel
          )}
        </Button>
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
            {fieldLabels.cancel}
          </Button>
        )}
      </div>
    </form>
  );
}
