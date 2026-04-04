import { useEffect, useMemo, useState } from "react";

import { InvoiceLineEditor } from "../../components/invoices/InvoiceLineEditor";
import { InvoiceTotalsCard } from "../../components/invoices/InvoiceTotalsCard";
import type { CustomerSummary } from "../../domain/customers/types";
import {
	INVOICE_TAX_POLICY_OPTIONS,
	type InvoiceBuyerType,
	type InvoiceCreatePayload,
	type InvoiceDraftLine,
	type InvoiceResponse,
} from "../../domain/invoices/types";
import { listCustomers } from "../../lib/api/customers";
import { createInvoice } from "../../lib/api/invoices";

interface DraftLine extends InvoiceDraftLine {
	id: number;
}

function roundMoney(value: number): number {
	return Math.round((value + Number.EPSILON) * 100) / 100;
}

function makeDraftLine(id: number): DraftLine {
	return {
		id,
		product_code: "",
		description: "",
		quantity: "1",
		unit_price: "0",
		tax_policy_code: "standard",
	};
}

function buildLinePreview(line: InvoiceDraftLine) {
	const quantity = Number(line.quantity);
	const unitPrice = Number(line.unit_price);
	const policy = INVOICE_TAX_POLICY_OPTIONS.find((option) => option.code === line.tax_policy_code)
		?? INVOICE_TAX_POLICY_OPTIONS[0];
	const subtotalAmount = Number.isFinite(quantity) && Number.isFinite(unitPrice)
		? roundMoney(quantity * unitPrice)
		: 0;
	const taxAmount = roundMoney(subtotalAmount * policy.taxRate);

	return {
		subtotalAmount,
		taxAmount,
		totalAmount: roundMoney(subtotalAmount + taxAmount),
		taxType: policy.taxType,
		taxRate: policy.taxRate,
	};
}

export default function CreateInvoicePage() {
	const [customers, setCustomers] = useState<CustomerSummary[]>([]);
	const [customerId, setCustomerId] = useState("");
	const [buyerType, setBuyerType] = useState<InvoiceBuyerType>("b2b");
	const [buyerIdentifier, setBuyerIdentifier] = useState("");
	const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().slice(0, 10));
	const [lines, setLines] = useState<DraftLine[]>([makeDraftLine(1)]);
	const [nextLineId, setNextLineId] = useState(2);
	const [submitting, setSubmitting] = useState(false);
	const [serverErrors, setServerErrors] = useState<Array<{ field: string; message: string }>>([]);
	const [created, setCreated] = useState<InvoiceResponse | null>(null);

	useEffect(() => {
		let active = true;
		void listCustomers({ status: "active", page_size: 200 }).then((response) => {
			if (active) {
				setCustomers(response.items);
			}
		});
		return () => {
			active = false;
		};
	}, []);

	const selectedCustomer = useMemo(
		() => customers.find((customer) => customer.id === customerId) ?? null,
		[customerId, customers],
	);

	useEffect(() => {
		if (buyerType === "b2c") {
			setBuyerIdentifier("");
			return;
		}
		if (selectedCustomer) {
			setBuyerIdentifier(selectedCustomer.normalized_business_number);
		}
	}, [buyerType, selectedCustomer]);

	const linePreviews = useMemo(() => lines.map((line) => buildLinePreview(line)), [lines]);
	const totals = useMemo(() => {
		return linePreviews.reduce(
			(accumulator, preview) => ({
				subtotalAmount: roundMoney(accumulator.subtotalAmount + preview.subtotalAmount),
				taxAmount: roundMoney(accumulator.taxAmount + preview.taxAmount),
				totalAmount: roundMoney(accumulator.totalAmount + preview.totalAmount),
			}),
			{ subtotalAmount: 0, taxAmount: 0, totalAmount: 0 },
		);
	}, [linePreviews]);

	const isValid = customerId.length > 0
		&& lines.length > 0
		&& lines.every((line) => {
			const quantity = Number(line.quantity);
			const unitPrice = Number(line.unit_price);
			return line.description.trim().length > 0
				&& Number.isFinite(quantity)
				&& quantity > 0
				&& Number.isFinite(unitPrice)
				&& unitPrice >= 0;
		})
		&& (buyerType === "b2c" || buyerIdentifier.trim().length > 0);

	function updateLine(lineId: number, next: InvoiceDraftLine) {
		setLines((current) => current.map((line) => (line.id === lineId ? { ...line, ...next } : line)));
	}

	function addLine() {
		setLines((current) => [...current, makeDraftLine(nextLineId)]);
		setNextLineId((current) => current + 1);
	}

	function removeLine(lineId: number) {
		setLines((current) => current.filter((line) => line.id !== lineId));
	}

	async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
		event.preventDefault();
		if (!isValid || submitting) {
			return;
		}

		setSubmitting(true);
		setServerErrors([]);
		const payload: InvoiceCreatePayload = {
			customer_id: customerId,
			buyer_type: buyerType,
			buyer_identifier: buyerType === "b2b" ? buyerIdentifier.trim() : null,
			invoice_date: invoiceDate,
			currency_code: "TWD",
			lines: lines.map((line) => ({
				product_code: line.product_code.trim() || null,
				description: line.description.trim(),
				quantity: line.quantity,
				unit_price: line.unit_price,
				tax_policy_code: line.tax_policy_code,
			})),
		};

		try {
			const result = await createInvoice(payload);
			if (result.ok) {
				setCreated(result.data);
				return;
			}
			setServerErrors(result.errors);
		} finally {
			setSubmitting(false);
		}
	}

	if (created) {
		return (
			<section className="hero-card">
				<h2>Invoice Created</h2>
				<p>
					<strong>{created.invoice_number}</strong> was issued for {created.currency_code} {created.total_amount}.
				</p>
				<button
					type="button"
					onClick={() => {
						setCreated(null);
						setCustomerId("");
						setBuyerType("b2b");
						setBuyerIdentifier("");
						setLines([makeDraftLine(1)]);
						setNextLineId(2);
					}}
				>
					Create Another Invoice
				</button>
			</section>
		);
	}

	return (
		<section className="hero-card">
			<h2>Create Invoice</h2>
			<form onSubmit={handleSubmit} style={{ display: "grid", gap: 16 }}>
				{serverErrors.length > 0 && (
					<div role="alert" style={{ color: "#dc2626" }}>
						{serverErrors.map((error) => (
							<div key={`${error.field}:${error.message}`}>{error.message}</div>
						))}
					</div>
				)}

				<label>
					Customer
					<select value={customerId} onChange={(event) => setCustomerId(event.target.value)} required>
						<option value="">-- Select customer --</option>
						{customers.map((customer) => (
							<option key={customer.id} value={customer.id}>
								{customer.company_name} ({customer.normalized_business_number})
							</option>
						))}
					</select>
				</label>

				<div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
					<label>
						Buyer Type
						<select
							value={buyerType}
							onChange={(event) => setBuyerType(event.target.value as InvoiceBuyerType)}
						>
							<option value="b2b">B2B</option>
							<option value="b2c">B2C</option>
						</select>
					</label>

					<label>
						Buyer Identifier
						<input
							type="text"
							value={buyerType === "b2c" ? "0000000000" : buyerIdentifier}
							onChange={(event) => setBuyerIdentifier(event.target.value)}
							disabled={buyerType === "b2c"}
							required={buyerType === "b2b"}
						/>
					</label>

					<label>
						Invoice Date
						<input
							type="date"
							value={invoiceDate}
							onChange={(event) => setInvoiceDate(event.target.value)}
							required
						/>
					</label>
				</div>

				{buyerType === "b2c" && (
					<p style={{ margin: 0, fontSize: "0.95rem" }}>
						B2C invoices store the MIG sentinel buyer identifier <strong>0000000000</strong>.
					</p>
				)}

				<div>
					<h3>Invoice Lines</h3>
					{lines.map((line, index) => (
						<InvoiceLineEditor
							key={line.id}
							index={index}
							line={line}
							preview={linePreviews[index]}
							currencyCode="TWD"
							canRemove={lines.length > 1}
							onChange={(next) => updateLine(line.id, next)}
							onRemove={() => removeLine(line.id)}
						/>
					))}
					<button type="button" onClick={addLine}>
						Add Line
					</button>
				</div>

				<InvoiceTotalsCard
					currencyCode="TWD"
					lineCount={lines.length}
					subtotalAmount={totals.subtotalAmount}
					taxAmount={totals.taxAmount}
					totalAmount={totals.totalAmount}
				/>

				{customers.length === 0 && (
					<p style={{ margin: 0 }}>No active customers are available yet.</p>
				)}

				<div style={{ display: "flex", gap: 12 }}>
					<button type="submit" disabled={!isValid || submitting || customers.length === 0}>
						{submitting ? "Creating..." : "Create Invoice"}
					</button>
				</div>
			</form>
		</section>
	);
}