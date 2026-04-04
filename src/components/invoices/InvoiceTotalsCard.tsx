interface InvoiceTotalsCardProps {
	currencyCode: string;
	lineCount: number;
	subtotalAmount: number;
	taxAmount: number;
	totalAmount: number;
}

function formatAmount(value: number): string {
	return value.toLocaleString("en-US", {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	});
}

export function InvoiceTotalsCard({
	currencyCode,
	lineCount,
	subtotalAmount,
	taxAmount,
	totalAmount,
}: InvoiceTotalsCardProps) {
	return (
		<section
			data-testid="invoice-totals-card"
			style={{ padding: 12, border: "1px solid #e5e7eb", borderRadius: 8 }}
		>
			<h3>Invoice Totals Preview</h3>
			<dl>
				<dt>Lines</dt>
				<dd>{lineCount}</dd>
				<dt>Subtotal</dt>
				<dd>{currencyCode} {formatAmount(subtotalAmount)}</dd>
				<dt>Tax</dt>
				<dd>{currencyCode} {formatAmount(taxAmount)}</dd>
				<dt>Grand Total</dt>
				<dd>{currencyCode} {formatAmount(totalAmount)}</dd>
			</dl>
		</section>
	);
}