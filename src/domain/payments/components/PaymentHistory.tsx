/** Display payment history for an invoice. */

import { usePayments } from "../hooks/usePayments";

interface PaymentHistoryProps {
	invoiceId: string;
}

export default function PaymentHistory({ invoiceId }: PaymentHistoryProps) {
	const { items, loading, error } = usePayments({ invoice_id: invoiceId });

	if (loading) return <p>Loading payments…</p>;
	if (error) return <p style={{ color: "red" }}>Error: {error}</p>;
	if (items.length === 0) return <p>No payments recorded.</p>;

	return (
		<div data-testid="payment-history">
			<h4>Payment History</h4>
			<table>
				<thead>
					<tr>
						<th>Reference</th>
						<th>Amount</th>
						<th>Method</th>
						<th>Date</th>
						<th>Recorded By</th>
					</tr>
				</thead>
				<tbody>
					{items.map((p) => (
						<tr key={p.id}>
							<td>{p.payment_ref}</td>
							<td>{p.amount}</td>
							<td>{p.payment_method}</td>
							<td>{p.payment_date}</td>
							<td>{p.created_by}</td>
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}
