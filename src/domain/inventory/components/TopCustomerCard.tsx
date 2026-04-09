/** Top customer card — displays top customer or empty state. */

import { SectionCard } from "@/components/layout/PageLayout";
import type { TopCustomer } from "../hooks/useProductTopCustomer";

interface TopCustomerCardProps {
  customer: TopCustomer | null;
  loading?: boolean;
}

export function TopCustomerCard({ customer, loading }: TopCustomerCardProps) {
  return (
    <SectionCard title="Top Customer">
      {loading ? (
        <div className="h-12 w-48 animate-pulse rounded-lg bg-muted" />
      ) : customer ? (
        <div className="flex items-baseline gap-3">
          <span className="font-semibold text-foreground">{customer.customer_name}</span>
          <span className="text-sm text-muted-foreground">
            {customer.total_qty.toLocaleString()} units total
          </span>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No orders yet.</p>
      )}
    </SectionCard>
  );
}
