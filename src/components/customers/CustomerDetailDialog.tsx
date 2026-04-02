/** Modal dialog showing full customer details. */

import { useEffect, useState } from "react";
import type { CustomerResponse } from "../../domain/customers/types";
import { getCustomer } from "../../lib/api/customers";

interface Props {
  customerId: string;
  onClose: () => void;
  onEdit?: () => void;
}

export function CustomerDetailDialog({ customerId, onClose, onEdit }: Props) {
  const [customer, setCustomer] = useState<CustomerResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getCustomer(customerId)
      .then((c) => {
        if (!cancelled) {
          setCustomer(c);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCustomer(null);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [customerId]);

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog-content" onClick={(e) => e.stopPropagation()}>
        <button className="dialog-close" onClick={onClose}>
          ✕
        </button>
        {loading ? (
          <p>Loading…</p>
        ) : !customer ? (
          <p>Customer not found.</p>
        ) : (
          <>
            <dl className="customer-detail">
              <dt>Company Name</dt>
              <dd>{customer.company_name}</dd>
              <dt>BAN</dt>
              <dd>{customer.normalized_business_number}</dd>
              <dt>Billing Address</dt>
              <dd>{customer.billing_address}</dd>
              <dt>Contact Name</dt>
              <dd>{customer.contact_name}</dd>
              <dt>Phone</dt>
              <dd>{customer.contact_phone}</dd>
              <dt>Email</dt>
              <dd>{customer.contact_email}</dd>
              <dt>Credit Limit</dt>
              <dd>{customer.credit_limit}</dd>
              <dt>Status</dt>
              <dd>{customer.status}</dd>
            </dl>
            {onEdit && (
              <button type="button" onClick={onEdit} style={{ marginTop: "1rem" }}>
                Edit
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
