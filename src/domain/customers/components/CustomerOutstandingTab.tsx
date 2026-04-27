/** Customer outstanding balance tab for the customer detail page. */

import { CustomerOutstanding } from "@/domain/customers/components/CustomerOutstanding";

interface CustomerOutstandingTabProps {
  customerId: string;
}

export function CustomerOutstandingTab({ customerId }: CustomerOutstandingTabProps) {
  return <CustomerOutstanding customerId={customerId} />;
}

