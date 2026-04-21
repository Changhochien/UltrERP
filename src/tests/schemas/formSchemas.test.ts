import { describe, expect, it } from "vitest";

import { customerFormSchema } from "../../lib/schemas/customer.schema";
import {
  createRecordPaymentFormSchema,
  unmatchedPaymentFormSchema,
} from "../../lib/schemas/payment.schema";

describe("customerFormSchema", () => {
  it("rejects invalid Taiwan business numbers through the shared refinement", () => {
    const result = customerFormSchema.safeParse({
      company_name: "Acme Trading",
      business_number: "04595258",
      billing_address: "No. 1 Harbor Road",
      contact_name: "Jane Doe",
      contact_phone: "02-1234-5678",
      contact_email: "sales@acme.com",
      credit_limit: "120.50",
    });

    expect(result.success).toBe(false);
    if (result.success) {
      return;
    }

    expect(
      result.error.issues.some(
        (issue) =>
          issue.path[0] === "business_number" &&
          issue.message === "Business number checksum is invalid.",
      ),
    ).toBe(true);
  });
});

describe("payment schemas", () => {
  it("rejects invoice payments above the outstanding balance", () => {
    const result = createRecordPaymentFormSchema(100).safeParse({
      amount: "150",
      payment_method: "BANK_TRANSFER",
      payment_date: "2026-04-01",
      reference_number: "",
      notes: "",
    });

    expect(result.success).toBe(false);
    if (result.success) {
      return;
    }

    expect(
      result.error.issues.some(
        (issue) =>
          issue.path[0] === "amount" &&
          issue.message === "payments.form.errors.amountExceedsOutstanding",
      ),
    ).toBe(true);
  });

  it("requires a customer before unmatched payments can be submitted", () => {
    const result = unmatchedPaymentFormSchema.safeParse({
      customer_id: "",
      amount: "125.50",
      payment_method: "BANK_TRANSFER",
      payment_date: "2026-04-01",
      reference_number: "",
      notes: "",
    });

    expect(result.success).toBe(false);
    if (result.success) {
      return;
    }

    expect(
      result.error.issues.some(
        (issue) =>
          issue.path[0] === "customer_id" &&
          issue.message === "payments.form.errors.customerRequired",
      ),
    ).toBe(true);
  });
});