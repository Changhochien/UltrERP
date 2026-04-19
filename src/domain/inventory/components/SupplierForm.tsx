import { useEffect, useState } from "react";

import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import type { Supplier, SupplierCreate } from "../types";

export interface SupplierFormFieldError {
  field: string;
  message: string;
}

export type SupplierFormSubmitResult =
  | { ok: true; supplier: Supplier }
  | { ok: false; fieldErrors?: SupplierFormFieldError[]; formError?: string };

export interface SupplierFormValues {
  name: string;
  contact_email: string;
  phone: string;
  address: string;
  default_lead_time_days: string;
}

interface SupplierFormProps {
  initialValues?: Partial<SupplierFormValues>;
  onSubmit: (values: SupplierCreate) => Promise<SupplierFormSubmitResult>;
  onSuccess: (supplier: Supplier) => void;
  onCancel?: () => void;
  submitLabel: string;
  submittingLabel: string;
}

const DEFAULT_VALUES: SupplierFormValues = {
  name: "",
  contact_email: "",
  phone: "",
  address: "",
  default_lead_time_days: "",
};

function toErrorMap(errors: SupplierFormFieldError[]): Record<string, string> {
  return errors.reduce<Record<string, string>>((acc, error) => {
    if (error.field) {
      acc[error.field] = error.message;
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
  const [formData, setFormData] = useState<SupplierFormValues>(DEFAULT_VALUES);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setFormData({
      name: initialValues?.name ?? DEFAULT_VALUES.name,
      contact_email: initialValues?.contact_email ?? DEFAULT_VALUES.contact_email,
      phone: initialValues?.phone ?? DEFAULT_VALUES.phone,
      address: initialValues?.address ?? DEFAULT_VALUES.address,
      default_lead_time_days:
        initialValues?.default_lead_time_days ?? DEFAULT_VALUES.default_lead_time_days,
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

  function validate(values: SupplierFormValues): Record<string, string> {
    const nextErrors: Record<string, string> = {};
    if (!values.name.trim()) {
      nextErrors.name = "Supplier name is required";
    }

    const leadTime = values.default_lead_time_days.trim();
    if (leadTime) {
      const numericLeadTime = Number(leadTime);
      if (!Number.isFinite(numericLeadTime) || numericLeadTime < 0) {
        nextErrors.default_lead_time_days = "Lead time must be zero or greater";
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
      const leadTime = formData.default_lead_time_days.trim();
      const result = await onSubmit({
        name: formData.name.trim(),
        contact_email: formData.contact_email.trim() || undefined,
        phone: formData.phone.trim() || undefined,
        address: formData.address.trim() || undefined,
        default_lead_time_days: leadTime === "" ? undefined : Number(leadTime),
      });

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
    <form onSubmit={handleSubmit} className="space-y-4">
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