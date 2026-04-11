/** Customer outstanding balance summary card. */

import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { useTranslation } from "react-i18next";
import { useCustomerOutstanding } from "../../invoices/hooks/useInvoices";

interface CustomerOutstandingProps {
  customerId: string;
}

export function CustomerOutstanding({ customerId }: CustomerOutstandingProps) {
  const { t } = useTranslation("common", { keyPrefix: "customer.detail.outstanding" });
  const { summary, loading, error } = useCustomerOutstanding(customerId);

  if (loading) {
    return <p>{t("loading", { defaultValue: "Loading outstanding…" })}</p>;
  }
  if (error) {
    return (
      <SurfaceMessage tone="danger">
        {t("error", { message: error, defaultValue: `Error: ${error}` })}
      </SurfaceMessage>
    );
  }
  if (!summary) return null;

  return (
    <SectionCard
      title={t("title", { defaultValue: "Outstanding Balance" })}
      description={t("description", { defaultValue: "Receivables posture for the selected customer." })}
      className="mb-4"
    >
      <div data-testid="customer-outstanding" className="space-y-4">
        <dl className="gap-y-4">
          <dt>{t("totalOutstanding", { defaultValue: "Total Outstanding" })}</dt>
          <dd className="text-xl font-semibold">
            {summary.currency_code} {summary.total_outstanding}
          </dd>
          <dt>{t("invoiceCount", { defaultValue: "Invoices" })}</dt>
          <dd>{summary.invoice_count}</dd>
          {summary.overdue_count > 0 ? (
            <>
              <dt>{t("overdue", { defaultValue: "Overdue" })}</dt>
              <dd>
                <Badge variant="destructive" className="normal-case tracking-normal">
                  {t("overdueSummary", {
                    count: summary.overdue_count,
                    currency: summary.currency_code,
                    amount: summary.overdue_amount,
                    defaultValue: `${summary.overdue_count} invoices (${summary.currency_code} ${summary.overdue_amount})`,
                  })}
                </Badge>
              </dd>
            </>
          ) : null}
        </dl>
      </div>
    </SectionCard>
  );
}
