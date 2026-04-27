/** Warning banner shown when a duplicate business number is detected during customer creation. */

import type { DuplicateInfo } from "@/lib/api/customers";
import { Button } from "@/components/ui/button";

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
    <div
      className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-foreground"
      role="alert"
    >
      <p>
        A customer with business number{" "}
        <strong>{duplicate.normalized_business_number}</strong> already exists:
      </p>
      <p className="mt-1 font-semibold">{duplicate.existing_customer_name}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button type="button" size="sm" onClick={() => onViewExisting(duplicate.existing_customer_id)}>
          View Existing Customer
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={onCancel}>
          Continue editing
        </Button>
      </div>
    </div>
  );
}
