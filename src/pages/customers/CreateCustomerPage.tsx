/** Create Customer page. */

import { useState } from "react";
import type { CustomerCreatePayload, CustomerResponse } from "../../domain/customers/types";
import { CUSTOMERS_ROUTE, type AppRoute } from "../../lib/routes";
import { createCustomer, type DuplicateInfo } from "../../lib/api/customers";
import CustomerForm from "../../components/customers/CustomerForm";
import DuplicateCustomerWarning from "../../components/customers/DuplicateCustomerWarning";

export interface CreateCustomerPageProps {
  onNavigate?: (path: AppRoute) => void;
}

export default function CreateCustomerPage({ onNavigate }: CreateCustomerPageProps) {
  const [submitting, setSubmitting] = useState(false);
  const [serverErrors, setServerErrors] = useState<Array<{ field: string; message: string }>>([]);
  const [created, setCreated] = useState<CustomerResponse | null>(null);
  const [duplicate, setDuplicate] = useState<DuplicateInfo | null>(null);

  async function handleSubmit(payload: CustomerCreatePayload) {
    setSubmitting(true);
    setServerErrors([]);
    setDuplicate(null);
    try {
      const result = await createCustomer(payload);
      if (result.ok) {
        setCreated(result.data);
      } else if (result.duplicate) {
        setDuplicate(result.duplicate);
      } else {
        setServerErrors(result.errors);
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (created) {
    return (
      <section className="hero-card">
        <h2>Customer Created</h2>
        <p>
          <strong>{created.company_name}</strong> ({created.normalized_business_number}) has been
          created with ID <code>{created.id}</code>.
        </p>
        <button type="button" onClick={() => setCreated(null)}>
          Create Another
        </button>
      </section>
    );
  }

  return (
    <section className="hero-card">
      <h2>Create Customer</h2>
      {duplicate && (
        <DuplicateCustomerWarning
          duplicate={duplicate}
          onViewExisting={() => onNavigate?.(CUSTOMERS_ROUTE)}
          onCancel={() => setDuplicate(null)}
        />
      )}
      {!duplicate && (
        <CustomerForm onSubmit={handleSubmit} submitting={submitting} serverErrors={serverErrors} />
      )}
    </section>
  );
}
