/**
 * InvoicePrintPreviewModal — full-screen preview with print action.
 *
 * Shows the InvoicePrintSheet at 1:1 scale so the clerk can verify
 * field placement against the pre-printed stationery before printing.
 */

import { useCallback } from "react";
import type {
	InvoiceResponse,
	PrintCustomerInfo,
	SellerInfo,
} from "../../../domain/invoices/types";
import InvoicePrintSheet from "./InvoicePrintSheet";

interface InvoicePrintPreviewModalProps {
	invoice: InvoiceResponse;
	customer: PrintCustomerInfo;
	seller: SellerInfo;
	onClose: () => void;
}

export default function InvoicePrintPreviewModal({
	invoice,
	customer,
	seller,
	onClose,
}: InvoicePrintPreviewModalProps) {
	const handlePrint = useCallback(() => {
		window.print();
	}, []);

	return (
		<div
			role="dialog"
			aria-label="Invoice print preview"
			style={{
				position: "fixed",
				inset: 0,
				backgroundColor: "rgba(0,0,0,0.6)",
				display: "flex",
				flexDirection: "column",
				alignItems: "center",
				zIndex: 9999,
				overflow: "auto",
			}}
		>
			{/* ── Controls (hidden during print) ── */}
			<div
				className="print-preview-controls"
				style={{
					display: "flex",
					gap: "1rem",
					padding: "1rem",
					backgroundColor: "#fff",
					width: "100%",
					justifyContent: "center",
					borderBottom: "1px solid #ddd",
				}}
			>
				<button
					type="button"
					onClick={handlePrint}
					style={{
						padding: "0.5rem 1.5rem",
						backgroundColor: "#2563eb",
						color: "#fff",
						border: "none",
						borderRadius: 4,
						fontWeight: 600,
						cursor: "pointer",
					}}
				>
					列印 (Print)
				</button>
				<button
					type="button"
					onClick={onClose}
					style={{
						padding: "0.5rem 1.5rem",
						backgroundColor: "#e5e7eb",
						border: "none",
						borderRadius: 4,
						cursor: "pointer",
					}}
				>
					關閉 (Close)
				</button>
			</div>

			{/* ── Preview surface ── */}
			<div
				style={{
					backgroundColor: "#fff",
					margin: "2rem",
					padding: "8mm 18mm 8mm 8mm",
					boxShadow: "0 4px 24px rgba(0,0,0,0.2)",
				}}
			>
				<InvoicePrintSheet
					invoice={invoice}
					customer={customer}
					seller={seller}
				/>
			</div>
		</div>
	);
}
