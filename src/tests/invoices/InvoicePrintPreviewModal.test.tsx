import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";

import InvoicePrintPreviewModal from "../../components/invoices/print/InvoicePrintPreviewModal";
import type {
	InvoiceLineResponse,
	InvoiceResponse,
	PrintCustomerInfo,
	SellerInfo,
} from "../../domain/invoices/types";

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

const seller: SellerInfo = {
	name: "UltrERP",
	address: "彰化市線東路一段臨670號",
	phone: "(04)7613535",
	fax: "(04)7613030",
};

const customer: PrintCustomerInfo = {
	company_name: "台灣好公司有限公司",
	billing_address: "台北市信義區信義路五段7號",
	contact_name: "王大明",
	contact_phone: "0912-345-678",
};

function makeLine(index: number): InvoiceLineResponse {
	return {
		id: `line-${index}`,
		product_id: null,
		product_code_snapshot: `SKU-${String(index).padStart(3, "0")}`,
		description: `Large Fixture Item ${index}`,
		quantity: String(index),
		unit_price: "100",
		subtotal_amount: String(index * 100),
		tax_type: 1,
		tax_rate: "0.05",
		tax_amount: String(index * 5),
		total_amount: String(index * 105),
		zero_tax_rate_reason: null,
	};
}

function makeInvoice(lineCount: number): InvoiceResponse {
	return {
		id: "inv-1",
		invoice_number: "AA00000001",
		invoice_date: "2026-04-01",
		customer_id: "cust-1",
		buyer_type: "B2B",
		buyer_identifier_snapshot: "12345678",
		currency_code: "TWD",
		subtotal_amount: String(lineCount * 100),
		tax_amount: String(lineCount * 5),
		total_amount: String(lineCount * 105),
		status: "issued",
		version: 1,
		voided_at: null,
		void_reason: null,
		created_at: "2026-04-01T00:00:00Z",
		updated_at: "2026-04-01T00:00:00Z",
		lines: Array.from({ length: lineCount }, (_, index) => makeLine(index + 1)),
	};
}

describe("InvoicePrintPreviewModal", () => {
	it("renders a representative large invoice fixture and signals preview readiness", async () => {
		const onPreviewReady = vi.fn();

		render(
			<InvoicePrintPreviewModal
				invoice={makeInvoice(120)}
				customer={customer}
				seller={seller}
				onClose={() => {}}
				onPreviewReady={onPreviewReady}
			/>,
		);

		expect(screen.getByRole("dialog", { name: "Invoice print preview" })).toBeTruthy();
		expect(screen.getByText("Large Fixture Item 1")).toBeTruthy();
		expect(screen.getByText("Large Fixture Item 120")).toBeTruthy();
		expect(document.querySelectorAll(".ips-grid tbody tr")).toHaveLength(120);

		await waitFor(() => {
			expect(onPreviewReady).toHaveBeenCalledTimes(1);
		});
	});
});