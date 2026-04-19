import { useEffect, useState } from "react";

import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
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

export interface ProductFormValues {
  code: string;
  name: string;
  category_id: string | null;
  category_name: string;
  description: string;
  unit: string;
  standard_cost: string;
}

interface ProductFormProps {
  initialValues?: Partial<ProductFormValues>;
  onSubmit: (values: ProductUpdate) => Promise<ProductFormSubmitResult>;
  onSuccess: (product: ProductResponse) => void;
  onCancel?: () => void;
  submitLabel: string;
  submittingLabel: string;
}

const DEFAULT_VALUES: ProductFormValues = {
  code: "",
  name: "",
  category_id: null,
  category_name: "",
  description: "",
  unit: "pcs",
  standard_cost: "",
};

function toErrorMap(errors: ProductFormFieldError[]): Record<string, string> {
  return errors.reduce<Record<string, string>>((acc, error) => {
    if (error.field) {
      acc[error.field] = error.message;
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
}: ProductFormProps) {
  const [formData, setFormData] = useState<ProductFormValues>(DEFAULT_VALUES);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setFormData({
      code: initialValues?.code ?? DEFAULT_VALUES.code,
      name: initialValues?.name ?? DEFAULT_VALUES.name,
      category_id: initialValues?.category_id ?? DEFAULT_VALUES.category_id,
      category_name: initialValues?.category_name ?? DEFAULT_VALUES.category_name,
      description: initialValues?.description ?? DEFAULT_VALUES.description,
      unit: initialValues?.unit ?? DEFAULT_VALUES.unit,
      standard_cost: initialValues?.standard_cost ?? DEFAULT_VALUES.standard_cost,
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

  function validate(values: ProductFormValues): Record<string, string> {
    const nextErrors: Record<string, string> = {};
    if (!values.code.trim()) {
      nextErrors.code = "Code is required";
    }
    if (!values.name.trim()) {
      nextErrors.name = "Name is required";
    }
    if (!values.unit.trim()) {
      nextErrors.unit = "Unit is required";
    }
    const standardCost = values.standard_cost.trim();
    if (standardCost) {
      const parsedValue = Number(standardCost);
      if (!Number.isFinite(parsedValue)) {
        nextErrors.standard_cost = "Standard cost must be a valid number";
      } else if (parsedValue < 0) {
        nextErrors.standard_cost = "Standard cost must be greater than or equal to 0";
      }
    }
    return nextErrors;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setServerError(null);

    const clientErrors = validate(formData);
    setErrors(clientErrors);
    if (Object.keys(clientErrors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await onSubmit({
        code: formData.code.trim(),
        name: formData.name.trim(),
        category_id: formData.category_id,
        description: formData.description.trim(),
        unit: formData.unit.trim(),
        standard_cost: formData.standard_cost.trim() ? formData.standard_cost.trim() : null,
      });

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
    <form onSubmit={handleSubmit} className="space-y-4">
      {serverError && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {serverError}
        </div>
      )}

      <div>
        <label htmlFor="product-code" className="block text-sm font-medium">
          Code <span className="text-destructive">*</span>
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
          Name <span className="text-destructive">*</span>
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
          Category
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
            placeholder="Search or create category…"
            allowCreate
            disabled={isSubmitting}
          />
        </div>
        {errors.category && <p className="mt-1 text-sm text-destructive">{errors.category}</p>}
      </div>

      <div>
        <label htmlFor="product-description" className="block text-sm font-medium">
          Description
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
          Unit <span className="text-destructive">*</span>
        </label>
        <div id="product-unit" className="mt-1">
          <UnitCombobox
            inputId="product-unit-trigger"
            ariaLabelledBy="product-unit-label"
            value={formData.unit}
            onChange={(unit) => setFormData((current) => ({ ...current, unit }))}
            onClear={() => setFormData((current) => ({ ...current, unit: "" }))}
            placeholder="Search unit…"
            disabled={isSubmitting}
          />
        </div>
        {errors.unit && <p className="mt-1 text-sm text-destructive">{errors.unit}</p>}
      </div>

      <div>
        <label htmlFor="product-standard-cost" className="block text-sm font-medium">
          Standard Cost
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
          {isSubmitting ? submittingLabel : submitLabel}
        </Button>
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
