import { cleanup, render, screen } from "@testing-library/react";
import i18n from "i18next";
import { afterEach, describe, expect, it } from "vitest";
import zhHantTranslations from "../../../public/locales/zh-Hant/common.json";

import InvoicePrintSheet from "@/domain/invoices/components/print/InvoicePrintSheet";
import type {
	InvoiceResponse,
	PrintCustomerInfo,
	SellerInfo,
} from "../../domain/invoices/types";
import { validatePrintReady } from "../../lib/print/invoices";

	afterEach(async () => {
	cleanup();
	if (!i18n.hasResourceBundle("zh-Hant", "common")) {
		i18n.addResourceBundle("zh-Hant", "common", zhHantTranslations, true, true);
	}
	await i18n.changeLanguage("en");
});

const seller: SellerInfo = {
	name: "TestCo",
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

function makeInvoice(overrides: Partial<InvoiceResponse> = {}): InvoiceResponse {
	return {
		id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
		invoice_number: "AB00000001",
		invoice_date: "2025-07-01",
		customer_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
		buyer_type: "B2B",
		buyer_identifier_snapshot: "04595257",
		currency_code: "TWD",
		subtotal_amount: "1000",
		tax_amount: "50",
		total_amount: "1050",
		status: "issued",
		version: 1,
		voided_at: null,
		void_reason: null,
		created_at: "2025-07-01T00:00:00Z",
		updated_at: "2025-07-01T00:00:00Z",
		lines: [
			{
				id: "11111111-1111-1111-1111-111111111111",
				product_id: null,
				product_code_snapshot: "W-001",
				description: "Widget A",
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

describe("InvoicePrintSheet", () => {
	it("renders invoice number", () => {
		render(
			<InvoicePrintSheet
				invoice={makeInvoice()}
				customer={customer}
				seller={seller}
			/>,
		);
		expect(screen.getByText("AB00000001")).toBeTruthy();
	});

	it("renders formatted date", () => {
		render(
			<InvoicePrintSheet
				invoice={makeInvoice({ invoice_date: "2025-01-15" })}
				customer={customer}
				seller={seller}
			/>,
		);
		expect(screen.getByText(/2025 年 01 月 15 日/)).toBeTruthy();
	});

	it("renders customer name and BAN", () => {
		render(
			<InvoicePrintSheet
				invoice={makeInvoice()}
				customer={customer}
				seller={seller}
			/>,
		);
		expect(screen.getByText("台灣好公司有限公司")).toBeTruthy();
		expect(screen.getByText("04595257")).toBeTruthy();
	});

	it("renders seller info", () => {
		render(
			<InvoicePrintSheet
				invoice={makeInvoice()}
				customer={customer}
				seller={seller}
			/>,
		);
		expect(screen.getByText("TestCo")).toBeTruthy();
		expect(screen.getByText("彰化市線東路一段臨670號")).toBeTruthy();
	});

	it("omits blank seller contact fields", () => {
		render(
			<InvoicePrintSheet
				invoice={makeInvoice()}
				customer={customer}
				seller={{
					name: "TestCo",
					address: "",
					phone: "",
					fax: "",
				}}
			/>,
		);

		expect(screen.getByText("TestCo")).toBeTruthy();
		expect(screen.queryByText(/TEL:/)).toBeNull();
	});

	it("renders line item product code and description", () => {
		render(
			<InvoicePrintSheet
				invoice={makeInvoice()}
				customer={customer}
				seller={seller}
			/>,
		);
		expect(screen.getByText("W-001")).toBeTruthy();
		expect(screen.getByText("Widget A")).toBeTruthy();
	});

	it("uses the pre-tax subtotal in the line amount column", async () => {
		await i18n.changeLanguage("en");

		render(
			<InvoicePrintSheet
				invoice={makeInvoice()}
				customer={customer}
				seller={seller}
			/>,
		);

		const amountCell = document.querySelector(
			".ips-grid tbody tr td.ips-col-amount",
		)?.textContent;

		expect(amountCell).toBe("1,000");
	});

	it("renders totals in footer", () => {
		render(
			<InvoicePrintSheet
				invoice={makeInvoice()}
				customer={customer}
				seller={seller}
			/>,
		);
		// formatAmount uses toLocaleString — check that totals appear
		const allText = document.querySelector(".ips-footer-right")?.textContent ?? "";
		expect(allText).toContain("1,000");
		expect(allText).toContain("50");
		expect(allText).toContain("1,050");
	});

	it("renders multiple line items", () => {
		const invoice = makeInvoice({
			lines: [
				{
					id: "line-1",
					product_id: null,
					product_code_snapshot: "A-001",
					description: "Item A",
					quantity: "5",
					unit_price: "100",
					subtotal_amount: "500",
					tax_type: 1,
					tax_rate: "0.05",
					tax_amount: "25",
					total_amount: "525",
					zero_tax_rate_reason: null,
				},
				{
					id: "line-2",
					product_id: null,
					product_code_snapshot: "B-002",
					description: "Item B",
					quantity: "3",
					unit_price: "200",
					subtotal_amount: "600",
					tax_type: 1,
					tax_rate: "0.05",
					tax_amount: "30",
					total_amount: "630",
					zero_tax_rate_reason: null,
				},
			],
		});
		render(
			<InvoicePrintSheet
				invoice={invoice}
				customer={customer}
				seller={seller}
			/>,
		);
		expect(screen.getByText("A-001")).toBeTruthy();
		expect(screen.getByText("B-002")).toBeTruthy();
	});

	it("renders English form labels in the English locale", async () => {
		await i18n.changeLanguage("en");

		render(
			<InvoicePrintSheet
				invoice={makeInvoice()}
				customer={customer}
				seller={seller}
			/>,
		);

		expect(screen.getByText("Document Number")).toBeTruthy();
		expect(screen.getByText("Customer Name", { exact: false })).toBeTruthy();
		expect(screen.getByRole("columnheader", { name: "Product Code" })).toBeTruthy();
		expect(screen.queryByText("單據號碼")).toBeNull();
	});

	it("renders Traditional Chinese form labels in the zh-Hant locale", async () => {
		if (!i18n.hasResourceBundle("zh-Hant", "common")) {
			i18n.addResourceBundle("zh-Hant", "common", zhHantTranslations, true, true);
		}
		await i18n.changeLanguage("zh-Hant");

		render(
			<InvoicePrintSheet
				invoice={makeInvoice()}
				customer={customer}
				seller={seller}
			/>,
		);
		expect(screen.getByRole("columnheader", { name: "產品編號" })).toBeTruthy();
		expect(screen.getByRole("columnheader", { name: "品名規格" })).toBeTruthy();
		expect(screen.getByRole("columnheader", { name: "數量" })).toBeTruthy();
		expect(screen.getByRole("columnheader", { name: "單位" })).toBeTruthy();
		expect(screen.getByRole("columnheader", { name: "單價" })).toBeTruthy();
		expect(screen.getByText("單據號碼")).toBeTruthy();
		expect(screen.getByText("客戶名稱", { exact: false })).toBeTruthy();
		expect(screen.queryByText("Document Number")).toBeNull();
	});
});

describe("validatePrintReady", () => {
	it("returns null for valid issued invoice", () => {
		expect(validatePrintReady(makeInvoice())).toBeNull();
	});

	it("rejects voided invoice", () => {
		expect(validatePrintReady(makeInvoice({ status: "voided" }))).toContain(
			"voided",
		);
	});

	it("rejects invoice with no lines", () => {
		expect(validatePrintReady(makeInvoice({ lines: [] }))).toContain(
			"no line items",
		);
	});

	it("rejects invoice with missing number", () => {
		expect(
			validatePrintReady(makeInvoice({ invoice_number: "" })),
		).toContain("missing");
	});
});
