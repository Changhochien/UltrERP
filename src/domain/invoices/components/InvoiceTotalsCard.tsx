import { useTranslation } from "react-i18next";

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
	const { t } = useTranslation("common");
	return (
		<section data-testid="invoice-totals-card" className="rounded-2xl border border-border/80 bg-muted/25 p-5 shadow-sm">
			<h3 className="text-base font-semibold tracking-tight">{t("invoice.totals.title")}</h3>
			<dl className="mt-4 grid gap-x-6 gap-y-3 sm:grid-cols-[minmax(0,12rem)_minmax(0,1fr)]">
				<dt>{t("invoice.totals.lines")}</dt>
				<dd>{lineCount}</dd>
				<dt>{t("invoice.totals.subtotal")}</dt>
				<dd>{currencyCode} {formatAmount(subtotalAmount)}</dd>
				<dt>{t("invoice.totals.tax")}</dt>
				<dd>{currencyCode} {formatAmount(taxAmount)}</dd>
				<dt>{t("invoice.totals.grandTotal")}</dt>
				<dd>{currencyCode} {formatAmount(totalAmount)}</dd>
			</dl>
		</section>
	);
}
