/** Customer outstanding balance summary card. */

import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { useCustomerOutstanding } from "../../invoices/hooks/useInvoices";

interface CustomerOutstandingProps {
  customerId: string;
}

export function CustomerOutstanding({ customerId }: CustomerOutstandingProps) {
  const { summary, loading, error } = useCustomerOutstanding(customerId);

  if (loading) return <p>Loading outstanding…</p>;
  if (error) return <SurfaceMessage tone="danger">Error: {error}</SurfaceMessage>;
  if (!summary) return null;

  return (
    <SectionCard
      title="Outstanding Balance"
      description="Receivables posture for the selected customer."
      className="mb-4"
    >
      <div data-testid="customer-outstanding" className="space-y-4">
        <dl className="gap-y-4">
          <dt>Total Outstanding</dt>
          <dd className="text-xl font-semibold">
            {summary.currency_code} {summary.total_outstanding}
          </dd>
          <dt>Invoices</dt>
          <dd>{summary.invoice_count}</dd>
          {summary.overdue_count > 0 ? (
            <>
              <dt>Overdue</dt>
              <dd>
                <Badge variant="destructive" className="normal-case tracking-normal">
                  {summary.overdue_count} invoices ({summary.currency_code} {summary.overdue_amount})
                </Badge>
              </dd>
            </>
          ) : null}
        </dl>
      </div>
    </SectionCard>
  );
}
