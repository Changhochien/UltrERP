import type { InvoiceDraftLine } from "../../domain/invoices/types";
import { INVOICE_TAX_POLICY_OPTIONS } from "../../domain/invoices/types";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Input } from "../ui/input";

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
		<fieldset className="space-y-4 rounded-2xl border border-border/80 bg-background/70 p-4 shadow-sm">
			<legend>Line {index + 1}</legend>
			<div className="grid gap-4">
				<label className="space-y-2">
					Product Code
					<Input
						type="text"
						value={line.product_code}
						onChange={(event) => onChange({ ...line, product_code: event.target.value })}
					/>
				</label>

				<label className="space-y-2">
					Description
					<Input
						type="text"
						value={line.description}
						onChange={(event) => onChange({ ...line, description: event.target.value })}
						required
					/>
				</label>

				<div className="grid gap-4 md:grid-cols-3">
					<label className="space-y-2">
						Quantity
						<Input
							type="number"
							step="0.001"
							min="0.001"
							value={line.quantity}
							onChange={(event) => onChange({ ...line, quantity: event.target.value })}
							required
						/>
					</label>

					<label className="space-y-2">
						Unit Price
						<Input
							type="number"
							step="0.01"
							min="0"
							value={line.unit_price}
							onChange={(event) => onChange({ ...line, unit_price: event.target.value })}
							required
						/>
					</label>

					<label className="space-y-2">
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

				<div className="grid gap-3 md:grid-cols-5">
					<Badge variant="outline" className="justify-center normal-case tracking-normal">Tax Type: {preview.taxType}</Badge>
					<Badge variant="outline" className="justify-center normal-case tracking-normal">Tax Rate: {(preview.taxRate * 100).toFixed(0)}%</Badge>
					<Badge variant="outline" className="justify-center normal-case tracking-normal">Subtotal: {currencyCode} {formatAmount(preview.subtotalAmount)}</Badge>
					<Badge variant="outline" className="justify-center normal-case tracking-normal">Tax: {currencyCode} {formatAmount(preview.taxAmount)}</Badge>
					<Badge variant="default" className="justify-center normal-case tracking-normal">Total: {currencyCode} {formatAmount(preview.totalAmount)}</Badge>
				</div>

				{canRemove && (
					<div>
						<Button type="button" variant="outline" onClick={onRemove}>
							Remove Line
						</Button>
					</div>
				)}
			</div>
		</fieldset>
	);
}