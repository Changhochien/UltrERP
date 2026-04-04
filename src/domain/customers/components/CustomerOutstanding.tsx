/** Customer outstanding balance summary card. */

import { useCustomerOutstanding } from "../../invoices/hooks/useInvoices";

interface CustomerOutstandingProps {
  customerId: string;
}

export function CustomerOutstanding({ customerId }: CustomerOutstandingProps) {
  const { summary, loading, error } = useCustomerOutstanding(customerId);

  if (loading) return <p>Loading outstanding…</p>;
  if (error) return <p style={{ color: "red" }}>Error: {error}</p>;
  if (!summary) return null;

  return (
    <div
      data-testid="customer-outstanding"
      style={{
        padding: 12,
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        marginBottom: 16,
      }}
    >
      <h4>Outstanding Balance</h4>
      <dl>
        <dt>Total Outstanding</dt>
        <dd style={{ fontWeight: 600, fontSize: "1.2em" }}>
          {summary.currency_code} {summary.total_outstanding}
        </dd>
        <dt>Invoices</dt>
        <dd>{summary.invoice_count}</dd>
        {summary.overdue_count > 0 && (
          <>
            <dt>Overdue</dt>
            <dd style={{ color: "#dc2626" }}>
              {summary.overdue_count} invoices ({summary.currency_code} {summary.overdue_amount})
            </dd>
          </>
        )}
      </dl>
    </div>
  );
}
