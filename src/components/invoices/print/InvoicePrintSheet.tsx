/**
 * InvoicePrintSheet — the single reusable renderer for preview, print, and PDF export.
 *
 * Layout spec: docs/invoices/stationery-spec.md
 * All data comes from persisted invoice snapshots, never from editable form state.
 */

import type {
	InvoiceResponse,
	PrintCustomerInfo,
	SellerInfo,
} from "../../../domain/invoices/types";
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

export default function InvoicePrintSheet({
	invoice,
	customer,
	seller,
}: InvoicePrintSheetProps) {
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
					<div>{seller.address}</div>
					<div>TEL:{seller.phone} FAX:{seller.fax}</div>
				</div>
			</div>

			{/* ── Date / Document Number ── */}
			<div className="ips-doc-row">
				<span className="ips-date">{formatDate(invoice.invoice_date)}</span>
				<span className="ips-doc-number">
					<span className="ips-field-label">單據號碼：</span>
					{invoice.invoice_number}
				</span>
			</div>

			{/* ── Customer Info ── */}
			<div className="ips-customer">
				<div className="ips-customer-left">
					<div>
						<span className="ips-field-label">客戶名稱：</span>
						{customer.company_name}
					</div>
					<div>
						<span className="ips-field-label">統一編號：</span>
						{invoice.buyer_identifier_snapshot}
					</div>
					<div>
						<span className="ips-field-label">發票地址：</span>
						{customer.billing_address}
					</div>
					{customer.shipping_address && (
						<div>
							<span className="ips-field-label">送貨地址：</span>
							{customer.shipping_address}
						</div>
					)}
				</div>
				<div className="ips-customer-right">
					<div>
						<span className="ips-field-label">聯絡電話：</span>
						{customer.contact_phone}
					</div>
					{customer.contact_fax && (
						<div>
							<span className="ips-field-label">傳真號碼：</span>
							{customer.contact_fax}
						</div>
					)}
					<div>
						<span className="ips-field-label">聯絡人員：</span>
						{customer.contact_name}
					</div>
				</div>
			</div>

			{/* ── Line Items Grid ── */}
			<table className="ips-grid">
				<thead>
					<tr>
						<th className="ips-col-code">產品編號</th>
						<th className="ips-col-desc">品名規格</th>
						<th className="ips-col-qty">數量</th>
						<th className="ips-col-unit">單位</th>
						<th className="ips-col-price">單價</th>
						<th className="ips-col-net">實價</th>
						<th className="ips-col-amount">金額</th>
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
							<td className="ips-col-unit">個</td>
							<td className="ips-col-price">
								{formatAmount(line.unit_price)}
							</td>
							<td className="ips-col-net">
								{formatAmount(line.subtotal_amount)}
							</td>
							<td className="ips-col-amount">
								{formatAmount(line.total_amount)}
							</td>
						</tr>
					))}
				</tbody>
			</table>

			{/* ── Footer ── */}
			<div className="ips-footer">
				<div className="ips-footer-left">
					<div className="ips-footer-row">
						<span className="ips-field-label">折讓</span>
						<span />
					</div>
					<div className="ips-footer-row">
						<span className="ips-field-label">未收款</span>
						<span />
					</div>
				</div>
				<div className="ips-footer-right">
					<div className="ips-footer-row">
						<span className="ips-field-label">{"合\u3000\u3000計"}</span>
						<span>{formatAmount(invoice.subtotal_amount)}</span>
					</div>
					<div className="ips-footer-row">
						<span className="ips-field-label">營業稅</span>
						<span>{formatAmount(invoice.tax_amount)}</span>
					</div>
					<div className="ips-footer-row">
						<span className="ips-field-label">{"總\u3000\u3000計"}</span>
						<span className="ips-total-amount">
							{formatAmount(invoice.total_amount)}
						</span>
					</div>
				</div>
			</div>

			<div className="ips-footer-notes">
				<div className="ips-footer-notes-left">
					<span className="ips-field-label">備註</span>
				</div>
				<div className="ips-footer-notes-right">
					<span className="ips-field-label">客戶簽收</span>
				</div>
			</div>

			{/* Copy label in right margin — pre-printed, shown in preview only */}
			<span className="ips-copy-label">第一聯：收執聯</span>
		</div>
	);
}
