/**
 * InvoicePrintPreviewModal — full-screen preview with print action.
 *
 * Shows the InvoicePrintSheet at 1:1 scale so the clerk can verify
 * field placement against the pre-printed stationery before printing.
 */

import { useCallback, useEffect } from "react";
import { Button } from "../../ui/button";
import { Dialog, DialogContent, DialogTitle } from "../../ui/dialog";
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
	onPreviewReady?: () => void;
}

export default function InvoicePrintPreviewModal({
	invoice,
	customer,
	seller,
	onClose,
	onPreviewReady,
}: InvoicePrintPreviewModalProps) {
	const handlePrint = useCallback(() => {
		window.print();
	}, []);

	useEffect(() => {
		if (!onPreviewReady) {
			return undefined;
		}

		if (typeof window === "undefined" || typeof window.requestAnimationFrame !== "function") {
			onPreviewReady();
			return undefined;
		}

		const frameId = window.requestAnimationFrame(() => {
			onPreviewReady();
		});

		return () => {
			window.cancelAnimationFrame(frameId);
		};
	}, [invoice.id, onPreviewReady]);

	return (
		<Dialog open onOpenChange={(open) => {
			if (!open) {
				onClose();
			}
		}}>
			<DialogContent className="print-preview-dialog" aria-describedby={undefined}>
				<DialogTitle className="sr-only">Invoice print preview</DialogTitle>
				<div className="print-preview-shell">
					<div className="print-preview-controls border-b border-border bg-background/95 backdrop-blur">
						<Button type="button" onClick={handlePrint}>
							列印 (Print)
						</Button>
						<Button type="button" variant="secondary" onClick={onClose}>
							關閉 (Close)
						</Button>
					</div>

					<div className="print-preview-surface">
						<InvoicePrintSheet
							invoice={invoice}
							customer={customer}
							seller={seller}
						/>
					</div>
				</div>
			</DialogContent>
		</Dialog>
	);
}
