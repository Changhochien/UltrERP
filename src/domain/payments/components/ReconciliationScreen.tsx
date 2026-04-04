/** Reconciliation screen for matching payments to invoices. */

import { useState } from "react";
import { useRunReconciliation, useConfirmMatch, useManualMatch } from "../hooks/useReconciliation";

export default function ReconciliationScreen() {
	const { result, isLoading, error, execute } = useRunReconciliation();
	const { execute: doConfirm, isLoading: confirming } = useConfirmMatch();
	const { execute: doManual, isLoading: matching } = useManualMatch();
	const [manualInvoiceIds, setManualInvoiceIds] = useState<Record<string, string>>({});
	const [actionMessage, setActionMessage] = useState<string | null>(null);

	const autoMatched = result?.details.filter((d) => d.match_status === "matched") ?? [];
	const suggested = result?.details.filter((d) => d.match_status === "suggested") ?? [];
	const unmatched = result?.details.filter((d) => d.match_status === "unmatched") ?? [];

	const handleConfirm = async (paymentRef: string, paymentId: string) => {
		const p = await doConfirm(paymentId);
		if (p) {
			setActionMessage(`Confirmed match for ${paymentRef}`);
			await execute();
		}
	};

	const handleManualMatch = async (paymentRef: string, paymentId: string) => {
		const invoiceId = manualInvoiceIds[paymentRef];
		if (!invoiceId) return;
		const p = await doManual(paymentId, invoiceId);
		if (p) {
			setActionMessage(`Manually matched ${paymentRef}`);
			await execute();
		}
	};

	return (
		<div data-testid="reconciliation-screen">
			<h2>Payment Reconciliation</h2>

			<button onClick={execute} disabled={isLoading}>
				{isLoading ? "Running…" : "Run Reconciliation"}
			</button>

			{error && <p style={{ color: "red" }}>Error: {error}</p>}
			{actionMessage && <p style={{ color: "green" }}>{actionMessage}</p>}

			{result && (
				<div>
					<p>
						Matched: {result.matched_count} | Suggested: {result.suggested_count} | Unmatched: {result.unmatched_count}
					</p>

					{autoMatched.length > 0 && (
						<section>
							<h3>Auto-Matched</h3>
							<table>
								<thead>
									<tr><th>Payment Ref</th><th>Invoice</th><th>Match Type</th></tr>
								</thead>
								<tbody>
									{autoMatched.map((d) => (
										<tr key={d.payment_ref}>
											<td>{d.payment_ref}</td>
											<td>{d.invoice_number}</td>
											<td>{d.match_type}</td>
										</tr>
									))}
								</tbody>
							</table>
						</section>
					)}

					{suggested.length > 0 && (
						<section>
							<h3>Suggested Matches</h3>
							<table>
								<thead>
									<tr><th>Payment Ref</th><th>Suggested Invoice</th><th>Actions</th></tr>
								</thead>
								<tbody>
									{suggested.map((d) => (
										<tr key={d.payment_ref}>
											<td>{d.payment_ref}</td>
											<td>{d.suggested_invoice_number}</td>
											<td>
												<button onClick={() => handleConfirm(d.payment_ref, d.payment_id)} disabled={confirming}>
													Confirm
												</button>
											</td>
										</tr>
									))}
								</tbody>
							</table>
						</section>
					)}

					{unmatched.length > 0 && (
						<section>
							<h3>Unmatched Payments</h3>
							<table>
								<thead>
									<tr><th>Payment Ref</th><th>Invoice ID</th><th>Actions</th></tr>
								</thead>
								<tbody>
									{unmatched.map((d) => (
										<tr key={d.payment_ref}>
											<td>{d.payment_ref}</td>
											<td>
												<input
													type="text"
													placeholder="Invoice ID"
													value={manualInvoiceIds[d.payment_ref] ?? ""}
													onChange={(e) =>
														setManualInvoiceIds((prev) => ({
															...prev,
															[d.payment_ref]: e.target.value,
														}))
													}
												/>
											</td>
											<td>
												<button
													onClick={() => handleManualMatch(d.payment_ref, d.payment_id)}
													disabled={matching || !manualInvoiceIds[d.payment_ref]}
												>
													Match
												</button>
											</td>
										</tr>
									))}
								</tbody>
							</table>
						</section>
					)}
				</div>
			)}
		</div>
	);
}
