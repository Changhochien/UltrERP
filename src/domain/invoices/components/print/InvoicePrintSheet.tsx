/**
 * InvoicePrintSheet — the single reusable renderer for preview, print, and PDF export.
 *
 * Layout spec: docs/invoices/stationery-spec.md
 * All data comes from persisted invoice snapshots, never from editable form state.
 */

import { useTranslation } from "react-i18next";
import type {
	InvoiceResponse,
	PrintCustomerInfo,
	SellerInfo,
} from "@/domain/invoices/types";
import "./invoice-print.css";

interface InvoicePrintSheetProps {
	invoice: InvoiceResponse;
	customer: PrintCustomerInfo;
	seller: SellerInfo;
}

function formatDate(iso: string): string {
	const d = new Date(iso);
	const y = d.getFullYear();
	const m = String(d.getMonth() + 1).padStart(2, "0");
	const day = String(d.getDate()).padStart(2, "0");
	return `${y} 年 ${m} 月 ${day} 日`;
}

function formatAmount(value: string): string {
	const n = Number(value);
	if (Number.isNaN(n)) return value;
	return n.toLocaleString("zh-TW", { minimumFractionDigits: 0 });
}

function formatSellerContactLine(seller: SellerInfo): string | null {
	const parts = [
		seller.phone ? `TEL:${seller.phone}` : null,
		seller.fax ? `FAX:${seller.fax}` : null,
	].filter(Boolean);

	if (parts.length === 0) {
		return null;
	}

	return parts.join("   ");
}

export default function InvoicePrintSheet({
	invoice,
	customer,
	seller,
}: InvoicePrintSheetProps) {
	const { t } = useTranslation("common");
	const sellerContactLine = formatSellerContactLine(seller);
	return (
		<div className="invoice-print-sheet">
			{/* ── Header ── */}
			<div className="ips-header">
				<div className="ips-header-left">
					{seller.logoUrl && (
						<img
							src={seller.logoUrl}
							alt={seller.name}
							className="ips-company-logo"
						/>
					)}
					<span className="ips-company-name">{seller.name}</span>
				</div>
				<div className="ips-header-right">
					{seller.address ? <div>{seller.address}</div> : null}
					{sellerContactLine ? <div>{sellerContactLine}</div> : null}
				</div>
			</div>

			{/* ── Date / Document Number ── */}
			<div className="ips-doc-row">
				<span className="ips-date">{formatDate(invoice.invoice_date)}</span>
				<span className="ips-doc-number">
					<span className="ips-field-label">{t("invoice.print.documentNumber")}</span>
					{invoice.invoice_number}
				</span>
			</div>

			{/* ── Customer Info ── */}
			<div className="ips-customer">
				<div className="ips-customer-left">
					<div>
						<span className="ips-field-label">{t("invoice.print.customerName")}</span>
						{customer.company_name}
					</div>
					<div>
						<span className="ips-field-label">{t("invoice.print.taxId")}</span>
						{invoice.buyer_identifier_snapshot}
					</div>
					<div>
						<span className="ips-field-label">{t("invoice.print.invoiceAddress")}</span>
						{customer.billing_address}
					</div>
					{customer.shipping_address && (
						<div>
							<span className="ips-field-label">{t("invoice.print.shippingAddress")}</span>
							{customer.shipping_address}
						</div>
					)}
				</div>
				<div className="ips-customer-right">
					<div>
						<span className="ips-field-label">{t("invoice.print.contactPhone")}</span>
						{customer.contact_phone}
					</div>
					{customer.contact_fax && (
						<div>
							<span className="ips-field-label">{t("invoice.print.faxNumber")}</span>
							{customer.contact_fax}
						</div>
					)}
					<div>
						<span className="ips-field-label">{t("invoice.print.contactPerson")}</span>
						{customer.contact_name}
					</div>
				</div>
			</div>

			{/* ── Line Items Grid ── */}
			<table className="ips-grid">
				<thead>
					<tr>
						<th className="ips-col-code">{t("invoice.print.col.productCode")}</th>
						<th className="ips-col-desc">{t("invoice.print.col.description")}</th>
						<th className="ips-col-qty">{t("invoice.print.col.quantity")}</th>
						<th className="ips-col-unit">{t("invoice.print.col.unit")}</th>
						<th className="ips-col-price">{t("invoice.print.col.unitPrice")}</th>
						<th className="ips-col-net">{t("invoice.print.col.netPrice")}</th>
						<th className="ips-col-amount">{t("invoice.print.col.amount")}</th>
					</tr>
				</thead>
				<tbody>
					{invoice.lines.map((line) => (
						<tr key={line.id}>
							<td className="ips-col-code">
								{line.product_code_snapshot ?? ""}
							</td>
							<td className="ips-col-desc">{line.description}</td>
							<td className="ips-col-qty">{line.quantity}</td>
							<td className="ips-col-unit">{t("invoice.print.unit")}</td>
							<td className="ips-col-price">
								{formatAmount(line.unit_price)}
							</td>
							<td className="ips-col-net">
								{formatAmount(line.subtotal_amount)}
							</td>
							<td className="ips-col-amount">
								{formatAmount(line.subtotal_amount)}
							</td>
						</tr>
					))}
				</tbody>
			</table>

			{/* ── Footer ── */}
			<div className="ips-footer">
				<div className="ips-footer-left">
					<div className="ips-footer-row">
						<span className="ips-field-label">{t("invoice.print.discount")}</span>
						<span />
					</div>
					<div className="ips-footer-row">
						<span className="ips-field-label">{t("invoice.print.unpaid")}</span>
						<span />
					</div>
				</div>
				<div className="ips-footer-right">
					<div className="ips-footer-row">
						<span className="ips-field-label">{t("invoice.print.subtotal")}</span>
						<span>{formatAmount(invoice.subtotal_amount)}</span>
					</div>
					<div className="ips-footer-row">
						<span className="ips-field-label">{t("invoice.print.tax")}</span>
						<span>{formatAmount(invoice.tax_amount)}</span>
					</div>
					<div className="ips-footer-row">
						<span className="ips-field-label">{t("invoice.print.total")}</span>
						<span className="ips-total-amount">
							{formatAmount(invoice.total_amount)}
						</span>
					</div>
				</div>
			</div>

			<div className="ips-footer-notes">
				<div className="ips-footer-notes-left">
					<span className="ips-field-label">{t("invoice.print.notes")}</span>
				</div>
				<div className="ips-footer-notes-right">
					<span className="ips-field-label">{t("invoice.print.customerSignature")}</span>
				</div>
			</div>

			{/* Copy label in right margin — pre-printed, shown in preview only */}
			<span className="ips-copy-label">第一聯：收執聯</span>
		</div>
	);
}
