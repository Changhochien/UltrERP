/** Warning banner shown when a duplicate business number is detected during customer creation. */

import type { DuplicateInfo } from "../../lib/api/customers";

export interface DuplicateCustomerWarningProps {
  duplicate: DuplicateInfo;
  onViewExisting: (customerId: string) => void;
  onCancel: () => void;
}

export default function DuplicateCustomerWarning({
  duplicate,
  onViewExisting,
  onCancel,
}: DuplicateCustomerWarningProps) {
  return (
    <div className="duplicate-warning" role="alert">
      <h3>Duplicate Business Number</h3>
      <p>
        A customer with business number{" "}
        <strong>{duplicate.normalized_business_number}</strong> already exists:
      </p>
      <p className="duplicate-existing-name">
        <strong>{duplicate.existing_customer_name}</strong>
      </p>
      <div className="duplicate-actions">
        <button type="button" onClick={() => onViewExisting(duplicate.existing_customer_id)}>
          View Existing Customer
        </button>
        <button type="button" className="btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
