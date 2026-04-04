/** Display payment history for an invoice. */

import { DataTable } from "../../../components/layout/DataTable";
import { usePayments } from "../hooks/usePayments";

interface PaymentHistoryProps {
	invoiceId: string;
}

export default function PaymentHistory({ invoiceId }: PaymentHistoryProps) {
	const { items, loading, error } = usePayments({ invoice_id: invoiceId });

	if (loading) return <p>Loading payments…</p>;
	if (error) return <p className="text-sm text-destructive">Error: {error}</p>;
	if (items.length === 0) return <p>No payments recorded.</p>;

	return (
		<div data-testid="payment-history">
			<h4 className="mb-4 text-base font-semibold tracking-tight">Payment History</h4>
			<DataTable
				columns={[
					{
						id: "payment_ref",
						header: "Reference",
						sortable: true,
						getSortValue: (payment) => payment.payment_ref,
						cell: (payment) => <span className="font-medium">{payment.payment_ref}</span>,
					},
					{
						id: "amount",
						header: "Amount",
						sortable: true,
						getSortValue: (payment) => Number(payment.amount),
						cell: (payment) => payment.amount,
					},
					{
						id: "payment_method",
						header: "Method",
						sortable: true,
						getSortValue: (payment) => payment.payment_method,
						cell: (payment) => payment.payment_method,
					},
					{
						id: "payment_date",
						header: "Date",
						sortable: true,
						getSortValue: (payment) => payment.payment_date,
						cell: (payment) => payment.payment_date,
					},
					{
						id: "created_by",
						header: "Recorded By",
						sortable: true,
						getSortValue: (payment) => payment.created_by,
						cell: (payment) => payment.created_by,
					},
				]}
				data={items}
				emptyTitle="No payments recorded."
				emptyDescription="Recorded payments for this invoice will appear here."
				getRowId={(payment) => payment.id}
			/>
		</div>
	);
}
