/** Reusable customer create/edit form component. */

import { useState } from "react";

import { SurfaceMessage } from "../layout/PageLayout";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import type { CustomerCreatePayload } from "../../domain/customers/types";
import { validateTaiwanBusinessNumber } from "../../lib/validation/taiwanBusinessNumber";

export interface CustomerFormProps {
  onSubmit: (payload: CustomerCreatePayload) => void;
  submitting?: boolean;
  serverErrors?: Array<{ field: string; message: string }>;
  initialValues?: Partial<CustomerCreatePayload>;
  submitLabel?: string;
  submittingLabel?: string;
}

const INITIAL: CustomerCreatePayload = {
  company_name: "",
  business_number: "",
  billing_address: "",
  contact_name: "",
  contact_phone: "",
  contact_email: "",
  credit_limit: "0.00",
};

export default function CustomerForm({
  onSubmit,
  submitting,
  serverErrors,
  initialValues,
  submitLabel = "Create Customer",
  submittingLabel = "Creating…",
}: CustomerFormProps) {
  const [form, setForm] = useState<CustomerCreatePayload>({ ...INITIAL, ...initialValues });
  const [clientErrors, setClientErrors] = useState<Record<string, string>>({});
  const formErrors = serverErrors?.filter((error) => !error.field) ?? [];

  function handleChange(field: keyof CustomerCreatePayload, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
    // Clear field-level error on edit
    setClientErrors((prev) => {
      const copy = { ...prev };
      delete copy[field];
      return copy;
    });
  }

  function validate(): Record<string, string> {
    const errs: Record<string, string> = {};

    if (!form.company_name.trim()) errs.company_name = "Company name is required.";

    const banResult = validateTaiwanBusinessNumber(form.business_number);
    if (!banResult.valid) errs.business_number = banResult.error ?? "Invalid business number.";

    if (!form.contact_name.trim()) errs.contact_name = "Contact name is required.";
    if (!form.contact_phone.trim()) errs.contact_phone = "Phone is required.";
    if (!form.contact_email.trim()) errs.contact_email = "Email is required.";

    const limit = Number(form.credit_limit);
    if (Number.isNaN(limit) || limit < 0) errs.credit_limit = "Credit limit must be non-negative.";

    return errs;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length > 0) {
      setClientErrors(errs);
      return;
    }
    onSubmit(form);
  }

  function fieldError(field: string): string | undefined {
    return clientErrors[field] ?? serverErrors?.find((e) => e.field === field)?.message;
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4" noValidate>
      {formErrors.length > 0 ? (
        <SurfaceMessage tone="danger" role="alert">
          {formErrors.map((error) => (
            <p key={error.message}>{error.message}</p>
          ))}
        </SurfaceMessage>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2">
          <span>Company Name *</span>
          <Input
            id="company_name"
            value={form.company_name}
            onChange={(e) => handleChange("company_name", e.target.value)}
            maxLength={200}
            required
          />
          {fieldError("company_name") ? (
            <span className="text-sm text-destructive" role="alert">{fieldError("company_name")}</span>
          ) : null}
        </label>

        <label className="space-y-2">
          <span>Business Number (統一編號) *</span>
          <Input
            id="business_number"
            value={form.business_number}
            onChange={(e) => handleChange("business_number", e.target.value)}
            maxLength={20}
            required
          />
          {fieldError("business_number") ? (
            <span className="text-sm text-destructive" role="alert">{fieldError("business_number")}</span>
          ) : null}
        </label>
      </div>

      <label className="space-y-2">
        <span>Billing Address</span>
        <Input
          id="billing_address"
          value={form.billing_address}
          onChange={(e) => handleChange("billing_address", e.target.value)}
          maxLength={500}
        />
      </label>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2">
          <span>Contact Name *</span>
          <Input
            id="contact_name"
            value={form.contact_name}
            onChange={(e) => handleChange("contact_name", e.target.value)}
            maxLength={100}
            required
          />
          {fieldError("contact_name") ? (
            <span className="text-sm text-destructive" role="alert">{fieldError("contact_name")}</span>
          ) : null}
        </label>

        <label className="space-y-2">
          <span>Contact Phone *</span>
          <Input
            id="contact_phone"
            value={form.contact_phone}
            onChange={(e) => handleChange("contact_phone", e.target.value)}
            maxLength={30}
            required
          />
          {fieldError("contact_phone") ? (
            <span className="text-sm text-destructive" role="alert">{fieldError("contact_phone")}</span>
          ) : null}
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2">
          <span>Contact Email *</span>
          <Input
            id="contact_email"
            type="email"
            value={form.contact_email}
            onChange={(e) => handleChange("contact_email", e.target.value)}
            maxLength={254}
            required
          />
          {fieldError("contact_email") ? (
            <span className="text-sm text-destructive" role="alert">{fieldError("contact_email")}</span>
          ) : null}
        </label>

        <label className="space-y-2">
          <span>Credit Limit</span>
          <Input
            id="credit_limit"
            type="number"
            step="0.01"
            min="0"
            value={form.credit_limit}
            onChange={(e) => handleChange("credit_limit", e.target.value)}
            required
          />
          {fieldError("credit_limit") ? (
            <span className="text-sm text-destructive" role="alert">{fieldError("credit_limit")}</span>
          ) : null}
        </label>
      </div>

      <div>
        <Button type="submit" disabled={submitting}>
          {submitting ? submittingLabel : submitLabel}
        </Button>
      </div>
    </form>
  );
}
