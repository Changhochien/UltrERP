/** Reusable customer create/edit form component. */

import { useState } from "react";
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
    <form onSubmit={handleSubmit} className="customer-form" noValidate>
      {formErrors.length > 0 && (
        <div className="form-error-summary" role="alert">
          {formErrors.map((error) => (
            <p key={error.message}>{error.message}</p>
          ))}
        </div>
      )}

      <div className="form-field">
        <label htmlFor="company_name">Company Name *</label>
        <input
          id="company_name"
          value={form.company_name}
          onChange={(e) => handleChange("company_name", e.target.value)}
          maxLength={200}
          required
        />
        {fieldError("company_name") && (
          <span className="field-error" role="alert">{fieldError("company_name")}</span>
        )}
      </div>

      <div className="form-field">
        <label htmlFor="business_number">Business Number (統一編號) *</label>
        <input
          id="business_number"
          value={form.business_number}
          onChange={(e) => handleChange("business_number", e.target.value)}
          maxLength={20}
          required
        />
        {fieldError("business_number") && (
          <span className="field-error" role="alert">{fieldError("business_number")}</span>
        )}
      </div>

      <div className="form-field">
        <label htmlFor="billing_address">Billing Address</label>
        <input
          id="billing_address"
          value={form.billing_address}
          onChange={(e) => handleChange("billing_address", e.target.value)}
          maxLength={500}
        />
      </div>

      <div className="form-field">
        <label htmlFor="contact_name">Contact Name *</label>
        <input
          id="contact_name"
          value={form.contact_name}
          onChange={(e) => handleChange("contact_name", e.target.value)}
          maxLength={100}
          required
        />
        {fieldError("contact_name") && (
          <span className="field-error" role="alert">{fieldError("contact_name")}</span>
        )}
      </div>

      <div className="form-field">
        <label htmlFor="contact_phone">Contact Phone *</label>
        <input
          id="contact_phone"
          value={form.contact_phone}
          onChange={(e) => handleChange("contact_phone", e.target.value)}
          maxLength={30}
          required
        />
        {fieldError("contact_phone") && (
          <span className="field-error" role="alert">{fieldError("contact_phone")}</span>
        )}
      </div>

      <div className="form-field">
        <label htmlFor="contact_email">Contact Email *</label>
        <input
          id="contact_email"
          type="email"
          value={form.contact_email}
          onChange={(e) => handleChange("contact_email", e.target.value)}
          maxLength={254}
          required
        />
        {fieldError("contact_email") && (
          <span className="field-error" role="alert">{fieldError("contact_email")}</span>
        )}
      </div>

      <div className="form-field">
        <label htmlFor="credit_limit">Credit Limit</label>
        <input
          id="credit_limit"
          type="number"
          step="0.01"
          min="0"
          value={form.credit_limit}
          onChange={(e) => handleChange("credit_limit", e.target.value)}
          required
        />
        {fieldError("credit_limit") && (
          <span className="field-error" role="alert">{fieldError("credit_limit")}</span>
        )}
      </div>

      <button type="submit" disabled={submitting}>
        {submitting ? submittingLabel : submitLabel}
      </button>
    </form>
  );
}
