import type { InvoiceDraftLine } from "../../domain/invoices/types";
import { INVOICE_TAX_POLICY_OPTIONS } from "../../domain/invoices/types";

interface InvoiceLinePreview {
	subtotalAmount: number;
	taxAmount: number;
	totalAmount: number;
	taxType: number;
	taxRate: number;
}

interface InvoiceLineEditorProps {
	index: number;
	line: InvoiceDraftLine;
	preview: InvoiceLinePreview;
	currencyCode: string;
	canRemove: boolean;
	onChange: (next: InvoiceDraftLine) => void;
	onRemove: () => void;
}

function formatAmount(value: number): string {
	return value.toLocaleString("en-US", {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	});
}

export function InvoiceLineEditor({
	index,
	line,
	preview,
	currencyCode,
	canRemove,
	onChange,
	onRemove,
}: InvoiceLineEditorProps) {
	return (
		<fieldset style={{ marginBottom: 16, padding: 12, border: "1px solid #e5e7eb", borderRadius: 8 }}>
			<legend>Line {index + 1}</legend>
			<div style={{ display: "grid", gap: 12 }}>
				<label>
					Product Code
					<input
						type="text"
						value={line.product_code}
						onChange={(event) => onChange({ ...line, product_code: event.target.value })}
					/>
				</label>

				<label>
					Description
					<input
						type="text"
						value={line.description}
						onChange={(event) => onChange({ ...line, description: event.target.value })}
						required
					/>
				</label>

				<div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
					<label>
						Quantity
						<input
							type="number"
							step="0.001"
							min="0.001"
							value={line.quantity}
							onChange={(event) => onChange({ ...line, quantity: event.target.value })}
							required
						/>
					</label>

					<label>
						Unit Price
						<input
							type="number"
							step="0.01"
							min="0"
							value={line.unit_price}
							onChange={(event) => onChange({ ...line, unit_price: event.target.value })}
							required
						/>
					</label>

					<label>
						Tax Policy
						<select
							value={line.tax_policy_code}
							onChange={(event) => onChange({ ...line, tax_policy_code: event.target.value as InvoiceDraftLine["tax_policy_code"] })}
						>
							{INVOICE_TAX_POLICY_OPTIONS.map((option) => (
								<option key={option.code} value={option.code}>
									{option.label}
								</option>
							))}
						</select>
					</label>
				</div>

				<div style={{ display: "grid", gap: 4, fontSize: "0.95rem" }}>
					<span>Tax Type: {preview.taxType}</span>
					<span>Tax Rate: {(preview.taxRate * 100).toFixed(0)}%</span>
					<span>Subtotal: {currencyCode} {formatAmount(preview.subtotalAmount)}</span>
					<span>Tax: {currencyCode} {formatAmount(preview.taxAmount)}</span>
					<span>Total: {currencyCode} {formatAmount(preview.totalAmount)}</span>
				</div>

				{canRemove && (
					<div>
						<button type="button" onClick={onRemove}>
							Remove Line
						</button>
					</div>
				)}
			</div>
		</fieldset>
	);
}