/** Modal dialog for editing an existing customer. */

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { CustomerCreatePayload, CustomerResponse } from "../../domain/customers/types";
import { getCustomer, updateCustomer } from "../../lib/api/customers";
import type { DuplicateInfo } from "../../lib/api/customers";
import CustomerForm from "./CustomerForm";
import DuplicateCustomerWarning from "./DuplicateCustomerWarning";
import { useToast } from "../../hooks/useToast";

interface Props {
  customerId: string;
  onClose: () => void;
  onSaved: () => void;
  onViewCustomer?: (customerId: string) => void;
}

export function EditCustomerDialog({ customerId, onClose, onSaved, onViewCustomer }: Props) {
  const { t } = useTranslation("common");
  const { error: showErrorToast, success: showSuccessToast } = useToast();
  const [customer, setCustomer] = useState<CustomerResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [serverErrors, setServerErrors] = useState<Array<{ field: string; message: string }>>([]);
  const [versionConflict, setVersionConflict] = useState(false);
  const [duplicate, setDuplicate] = useState<DuplicateInfo | null>(null);

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

  async function handleSubmit(payload: CustomerCreatePayload) {
    if (!customer) return;
    setSubmitting(true);
    setServerErrors([]);
    setVersionConflict(false);
    setDuplicate(null);

    let result;
    try {
      result = await updateCustomer(customerId, {
        ...payload,
        version: customer.version,
      });
    } finally {
      setSubmitting(false);
    }

    if (result.ok) {
      showSuccessToast(
        t("customer.detail.toast.updatedTitle"),
        t("customer.detail.toast.updatedDescription", { name: result.data.company_name }),
      );
      onSaved();
      return;
    }

    if (result.versionConflict) {
      setVersionConflict(true);
      return;
    }

    if (result.duplicate) {
      setDuplicate(result.duplicate);
      return;
    }

    setServerErrors(result.errors);
    showErrorToast(
      t("customer.detail.toast.updateErrorTitle"),
      result.errors[0]?.message ?? t("customer.detail.toast.updateErrorDescription"),
    );
  }

  function toFormValues(c: CustomerResponse): CustomerCreatePayload {
    return {
      company_name: c.company_name,
      business_number: c.normalized_business_number,
      billing_address: c.billing_address,
      contact_name: c.contact_name,
      contact_phone: c.contact_phone,
      contact_email: c.contact_email,
      credit_limit: c.credit_limit,
    };
  }

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog-content" onClick={(e) => e.stopPropagation()}>
        <button className="dialog-close" onClick={onClose}>
          ✕
        </button>
        <h3>Edit Customer</h3>
        {loading ? (
          <p>Loading…</p>
        ) : !customer ? (
          <p>Customer not found.</p>
        ) : (
          <>
            {versionConflict && (
              <div className="version-conflict-warning" role="alert">
                <strong>Version conflict:</strong> This customer was modified by another user.
                Please close and reopen to get the latest version.
              </div>
            )}
            {duplicate && (
              <DuplicateCustomerWarning
                duplicate={duplicate}
                onViewExisting={(id) => {
                  onClose();
                  onViewCustomer?.(id);
                }}
                onCancel={() => setDuplicate(null)}
              />
            )}
            {!versionConflict && !duplicate && (
              <CustomerForm
                onSubmit={handleSubmit}
                submitting={submitting}
                serverErrors={serverErrors}
                initialValues={toFormValues(customer)}
                submitLabel="Save Changes"
                submittingLabel="Saving…"
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
