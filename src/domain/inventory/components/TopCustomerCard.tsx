/** Top customer card — displays top customer or empty state. */

import { useTranslation } from "react-i18next";

import { SectionCard } from "@/components/layout/PageLayout";
import type { TopCustomer } from "../hooks/useProductTopCustomer";

interface TopCustomerCardProps {
  customer: TopCustomer | null;
  loading?: boolean;
}

export function TopCustomerCard({ customer, loading }: TopCustomerCardProps) {
  const { t } = useTranslation("common", {
    keyPrefix: "inventory.productDetail.analyticsTab.topCustomer",
  });

  return (
    <SectionCard title={t("title")}>
      {loading ? (
        <div className="h-12 w-48 animate-pulse rounded-lg bg-muted" />
      ) : customer ? (
        <div className="flex items-baseline gap-3">
          <span className="font-semibold text-foreground">{customer.customer_name}</span>
          <span className="text-sm text-muted-foreground">
            {t("totalUnits", { count: customer.total_qty })}
          </span>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">{t("empty")}</p>
      )}
    </SectionCard>
  );
}
