import { useEffect, useState } from "react";

import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import {
  defaultSupplierFormValues,
  supplierFormSchema,
  toSupplierCreatePayload,
  type SupplierFormValues,
} from "../../../lib/schemas/supplier.schema";
import type { Supplier, SupplierCreate } from "../types";

export interface SupplierFormFieldError {
  field: string;
  message: string;
}

export type SupplierFormSubmitResult =
  | { ok: true; supplier: Supplier }
  | { ok: false; fieldErrors?: SupplierFormFieldError[]; formError?: string };

interface SupplierFormProps {
  initialValues?: Partial<SupplierFormValues>;
  onSubmit: (values: SupplierCreate) => Promise<SupplierFormSubmitResult>;
  onSuccess: (supplier: Supplier) => void;
  onCancel?: () => void;
  submitLabel: string;
  submittingLabel: string;
}

function toErrorMap(errors: SupplierFormFieldError[]): Record<string, string> {
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

export function SupplierForm({
  initialValues,
  onSubmit,
  onSuccess,
  onCancel,
  submitLabel,
  submittingLabel,
}: SupplierFormProps) {
  const [formData, setFormData] = useState<SupplierFormValues>(defaultSupplierFormValues);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setFormData({
      name: initialValues?.name ?? defaultSupplierFormValues.name,
      contact_email: initialValues?.contact_email ?? defaultSupplierFormValues.contact_email,
      phone: initialValues?.phone ?? defaultSupplierFormValues.phone,
      address: initialValues?.address ?? defaultSupplierFormValues.address,
      default_lead_time_days:
        initialValues?.default_lead_time_days ?? defaultSupplierFormValues.default_lead_time_days,
    });
    setErrors({});
    setServerError(null);
  }, [
    initialValues?.address,
    initialValues?.contact_email,
    initialValues?.default_lead_time_days,
    initialValues?.name,
    initialValues?.phone,
  ]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setServerError(null);

    const parsedValues = supplierFormSchema.safeParse(formData);
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
      const result = await onSubmit(toSupplierCreatePayload(parsedValues.data));

      if (result.ok) {
        onSuccess(result.supplier);
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
      {serverError ? (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {serverError}
        </div>
      ) : null}

      <div>
        <label htmlFor="supplier-name" className="block text-sm font-medium">
          Supplier Name <span className="text-destructive">*</span>
        </label>
        <Input
          id="supplier-name"
          type="text"
          value={formData.name}
          onChange={(event) => setFormData((current) => ({ ...current, name: event.target.value }))}
          aria-invalid={Boolean(errors.name)}
          disabled={isSubmitting}
        />
        {errors.name ? <p className="mt-1 text-sm text-destructive">{errors.name}</p> : null}
      </div>

      <div>
        <label htmlFor="supplier-contact-email" className="block text-sm font-medium">
          Contact Email
        </label>
        <Input
          id="supplier-contact-email"
          type="email"
          value={formData.contact_email}
          onChange={(event) =>
            setFormData((current) => ({ ...current, contact_email: event.target.value }))
          }
          disabled={isSubmitting}
        />
      </div>

      <div>
        <label htmlFor="supplier-phone" className="block text-sm font-medium">
          Phone
        </label>
        <Input
          id="supplier-phone"
          type="text"
          value={formData.phone}
          onChange={(event) => setFormData((current) => ({ ...current, phone: event.target.value }))}
          disabled={isSubmitting}
        />
      </div>

      <div>
        <label htmlFor="supplier-address" className="block text-sm font-medium">
          Address
        </label>
        <Textarea
          id="supplier-address"
          value={formData.address}
          onChange={(event) => setFormData((current) => ({ ...current, address: event.target.value }))}
          rows={4}
          disabled={isSubmitting}
        />
      </div>

      <div>
        <label htmlFor="supplier-default-lead-time" className="block text-sm font-medium">
          Default Lead Time (days)
        </label>
        <Input
          id="supplier-default-lead-time"
          type="number"
          min={0}
          value={formData.default_lead_time_days}
          onChange={(event) =>
            setFormData((current) => ({ ...current, default_lead_time_days: event.target.value }))
          }
          aria-invalid={Boolean(errors.default_lead_time_days)}
          disabled={isSubmitting}
        />
        {errors.default_lead_time_days ? (
          <p className="mt-1 text-sm text-destructive">{errors.default_lead_time_days}</p>
        ) : null}
      </div>

      <div className="flex gap-2">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? submittingLabel : submitLabel}
        </Button>
        {onCancel ? (
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
      </div>
    </form>
  );
}