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
		<section data-testid="invoice-totals-card" className="rounded-2xl border border-border/80 bg-muted/25 p-5 shadow-sm">
			<h3 className="text-base font-semibold tracking-tight">Invoice Totals Preview</h3>
			<dl className="mt-4 gap-y-4">
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