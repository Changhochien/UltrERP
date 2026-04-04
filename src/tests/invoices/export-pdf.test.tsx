/**
 * Tests for InvoiceExportButton and exportInvoicePdf helper.
 */

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import InvoiceExportButton from "../../components/invoices/InvoiceExportButton";
import type { InvoiceResponse } from "../../domain/invoices/types";
import { exportInvoicePdf } from "../../lib/pdf/invoices";

function makeInvoice(overrides: Partial<InvoiceResponse> = {}): InvoiceResponse {
	return {
		id: "aaaaaaaa-0000-0000-0000-000000000001",
		invoice_number: "AA00000001",
		invoice_date: "2025-03-15",
		customer_id: "bbbbbbbb-0000-0000-0000-000000000001",
		buyer_type: "B2B",
		buyer_identifier_snapshot: "12345678",
		currency_code: "TWD",
		subtotal_amount: "1000",
		tax_amount: "50",
		total_amount: "1050",
		status: "issued",
		version: 1,
		voided_at: null,
		void_reason: null,
		created_at: "2025-03-15T00:00:00Z",
		updated_at: "2025-03-15T00:00:00Z",
		lines: [
			{
				id: "cccccccc-0000-0000-0000-000000000001",
				product_id: null,
				product_code_snapshot: "A001",
				description: "Test item",
				quantity: "10",
				unit_price: "100",
				subtotal_amount: "1000",
				tax_type: 1,
				tax_rate: "0.05",
				tax_amount: "50",
				total_amount: "1050",
				zero_tax_rate_reason: null,
			},
		],
		...overrides,
	};
}

// ── InvoiceExportButton ─────────────────────────────────────────────

describe("InvoiceExportButton", () => {
	afterEach(() => cleanup());

	it("renders enabled for valid invoice", () => {
		render(<InvoiceExportButton invoice={makeInvoice()} />);
		const btn = screen.getByRole("button", { name: /export pdf/i });
		expect(btn).toBeTruthy();
		expect((btn as HTMLButtonElement).disabled).toBe(false);
	});

	it("is disabled for voided invoice", () => {
		render(
			<InvoiceExportButton invoice={makeInvoice({ status: "voided" })} />,
		);
		const btn = screen.getByRole("button", { name: /export pdf/i });
		expect((btn as HTMLButtonElement).disabled).toBe(true);
	});

	it("is disabled for invoice with no lines", () => {
		render(
			<InvoiceExportButton invoice={makeInvoice({ lines: [] })} />,
		);
		const btn = screen.getByRole("button", { name: /export pdf/i });
		expect((btn as HTMLButtonElement).disabled).toBe(true);
	});
});

// ── exportInvoicePdf ────────────────────────────────────────────────

describe("exportInvoicePdf", () => {
	const origFetch = globalThis.fetch;

	beforeEach(() => {
		globalThis.fetch = vi.fn();
	});

	afterEach(() => {
		globalThis.fetch = origFetch;
	});

	it("returns ok with filename on success", async () => {
		const blob = new Blob(["%PDF-1.4"], { type: "application/pdf" });
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: true,
			headers: new Headers({
				"Content-Disposition": 'attachment; filename="invoice-AA00000001.pdf"',
			}),
			blob: () => Promise.resolve(blob),
		});

		// Stub DOM download APIs missing in jsdom
		const mockAnchor = {
			href: "",
			download: "",
			click: vi.fn(),
		} as unknown as HTMLAnchorElement;
		vi.spyOn(document, "createElement").mockReturnValueOnce(mockAnchor);
		vi.spyOn(document.body, "appendChild").mockImplementation(() => mockAnchor);
		vi.spyOn(document.body, "removeChild").mockImplementation(() => mockAnchor);
		globalThis.URL.createObjectURL = vi.fn(() => "blob:test");
		globalThis.URL.revokeObjectURL = vi.fn();

		const result = await exportInvoicePdf("test-id");
		expect(result.ok).toBe(true);
		if (result.ok) {
			expect(result.filename).toBe("invoice-AA00000001.pdf");
		}
	});

	it("returns error on 404", async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: false,
			status: 404,
			json: () => Promise.resolve({ detail: "Invoice not found" }),
		});

		const result = await exportInvoicePdf("missing-id");
		expect(result.ok).toBe(false);
		if (!result.ok) {
			expect(result.status).toBe(404);
			expect(result.message).toBe("Invoice not found");
		}
	});

	it("returns error on 422 voided", async () => {
		(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: false,
			status: 422,
			json: () =>
				Promise.resolve({
					errors: [{ field: "invoice", message: "Cannot export a voided invoice to PDF." }],
				}),
		});

		const result = await exportInvoicePdf("voided-id");
		expect(result.ok).toBe(false);
		if (!result.ok) {
			expect(result.message).toContain("voided");
		}
	});
});
