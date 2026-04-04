/** Reconciliation screen for matching payments to invoices. */

import { useState } from "react";

import { DataTable } from "../../../components/layout/DataTable";
import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
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

	const summaryText = result
		? `Matched: ${result.matched_count} | Suggested: ${result.suggested_count} | Unmatched: ${result.unmatched_count}`
		: null;

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
		<div className="space-y-4" data-testid="reconciliation-screen">
			<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
				<div>
					<h2 className="text-lg font-semibold tracking-tight">Payment Reconciliation</h2>
					<p className="text-sm text-muted-foreground">Run matching across posted payments, confirm suggestions, and manually assign exceptions.</p>
				</div>
				<Button type="button" onClick={execute} disabled={isLoading}>
					{isLoading ? "Running…" : "Run Reconciliation"}
				</Button>
			</div>

			{error ? <SurfaceMessage tone="danger">Error: {error}</SurfaceMessage> : null}
			{actionMessage ? <SurfaceMessage tone="success">{actionMessage}</SurfaceMessage> : null}

			{summaryText ? (
				<div className="flex flex-wrap items-center gap-2">
					<p className="sr-only">{summaryText}</p>
					<Badge variant="success" className="normal-case tracking-normal">Matched: {result?.matched_count}</Badge>
					<Badge variant="warning" className="normal-case tracking-normal">Suggested: {result?.suggested_count}</Badge>
					<Badge variant="outline" className="normal-case tracking-normal">Unmatched: {result?.unmatched_count}</Badge>
				</div>
			) : null}

			{result ? (
				<div className="grid gap-4 xl:grid-cols-3">
					{autoMatched.length > 0 ? (
						<SectionCard title="Auto-Matched" description="Payments confidently linked without operator review.">
							<DataTable
								columns={[
									{ id: "payment_ref", header: "Payment Ref", sortable: true, getSortValue: (item) => item.payment_ref, cell: (item) => item.payment_ref },
									{ id: "invoice_number", header: "Invoice", sortable: true, getSortValue: (item) => item.invoice_number ?? "", cell: (item) => item.invoice_number ?? "-" },
									{ id: "match_type", header: "Match Type", sortable: true, getSortValue: (item) => item.match_type ?? "", cell: (item) => item.match_type ?? "-" },
								]}
								data={autoMatched}
								emptyTitle="No auto-matched payments."
								emptyDescription="Confirmed system matches will appear here."
								getRowId={(item) => item.payment_id}
							/>
						</SectionCard>
					) : null}

					{suggested.length > 0 ? (
						<SectionCard title="Suggested Matches" description="Review and confirm high-confidence candidate links.">
							<DataTable
								columns={[
									{ id: "payment_ref", header: "Payment Ref", sortable: true, getSortValue: (item) => item.payment_ref, cell: (item) => item.payment_ref },
									{ id: "suggested_invoice_number", header: "Suggested Invoice", sortable: true, getSortValue: (item) => item.suggested_invoice_number ?? "", cell: (item) => item.suggested_invoice_number ?? "-" },
									{
										id: "actions",
										header: "Actions",
										cell: (item) => (
											<Button type="button" size="sm" onClick={() => handleConfirm(item.payment_ref, item.payment_id)} disabled={confirming}>
												Confirm
											</Button>
										),
									},
								]}
								data={suggested}
								emptyTitle="No suggested matches."
								emptyDescription="Candidate invoice links will appear here when reconciliation finds them."
								getRowId={(item) => item.payment_id}
							/>
						</SectionCard>
					) : null}

					{unmatched.length > 0 ? (
						<SectionCard title="Unmatched Payments" description="Assign invoice IDs manually for remaining exceptions.">
							<DataTable
								columns={[
									{ id: "payment_ref", header: "Payment Ref", sortable: true, getSortValue: (item) => item.payment_ref, cell: (item) => item.payment_ref },
									{
										id: "invoice_id",
										header: "Invoice ID",
										cell: (item) => (
											<Input
												type="text"
												placeholder="Invoice ID"
												value={manualInvoiceIds[item.payment_ref] ?? ""}
												onChange={(event) =>
													setManualInvoiceIds((prev) => ({
														...prev,
														[item.payment_ref]: event.target.value,
													}))
												}
											/>
										),
									},
									{
										id: "actions",
										header: "Actions",
										cell: (item) => (
											<Button
												type="button"
												size="sm"
												onClick={() => handleManualMatch(item.payment_ref, item.payment_id)}
												disabled={matching || !manualInvoiceIds[item.payment_ref]}
											>
												Match
											</Button>
										),
									},
								]}
								data={unmatched}
								emptyTitle="No unmatched payments."
								emptyDescription="Outstanding unmatched payments will appear here."
								getRowId={(item) => item.payment_id}
							/>
						</SectionCard>
					) : null}
				</div>
			) : null}
		</div>
	);
}
