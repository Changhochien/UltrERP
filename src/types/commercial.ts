/**
 * Commercial currency types for Epic 25
 */

/**
 * Source of a commercial value on a document
 */
export type CommercialValueSource =
  | "source_document"
  | "profile_default"
  | "legacy_compatibility"
  | "manual_override";

/**
 * Money amount with both transaction and base currency values
 */
export interface MoneyAmount {
  transactionAmount: number;
  transactionCurrency: string;
  baseAmount: number;
  baseCurrency: string;
  conversionRate: number;
  effectiveDate: string;
  rateSource: string | null;
}

/**
 * Currency snapshot stored on a document
 */
export interface CurrencySnapshot {
  currencyCode: string;
  conversionRate: number;
  effectiveDate: string;
  rateSource: string | null;
  source: CommercialValueSource;
}

/**
 * FX conversion metadata for display
 */
export interface FXConversionMetadata {
  rate: string;
  effectiveDate: string;
  source: string;
  sourceLabel: string;
}

/**
 * Dual currency display for documents
 */
export interface DualCurrencyDisplay {
  transaction: {
    amount: string;
    currency: string;
    symbol: string;
  };
  base: {
    amount: string;
    currency: string;
    symbol: string;
  };
  rate: string;
  effectiveDate: string;
}

/**
 * Payment schedule row
 */
export interface PaymentScheduleRow {
  id: string;
  rowNumber: number;
  invoicePortion: number;
  dueDate: string;
  paymentAmount: string;
  outstandingAmount: string;
  paidAmount: string;
  isPaid: boolean;
  paidDate: string | null;
  discountPercent: number | null;
  discountValidityDays: number | null;
  modeOfPayment: string | null;
}

/**
 * Payment terms template detail
 */
export interface PaymentTermsTemplateDetail {
  id: string;
  rowNumber: number;
  invoicePortion: number;
  creditDays: number;
  creditMonths: number;
  discountPercent: number | null;
  discountValidityDays: number | null;
  modeOfPayment: string | null;
  description: string | null;
}

/**
 * Payment terms template
 */
export interface PaymentTermsTemplate {
  id: string;
  templateName: string;
  description: string | null;
  allocatePaymentBasedOnPaymentTerms: boolean;
  isActive: boolean;
  legacyCode: string | null;
  details: PaymentTermsTemplateDetail[];
}

/**
 * Customer commercial profile
 */
export interface CustomerCommercialProfile {
  defaultCurrencyCode: string | null;
  paymentTermsTemplateId: string | null;
  paymentTermsTemplate: PaymentTermsTemplate | null;
  creditLimit: number;
  defaultDiscountPercent: number;
}

/**
 * Supplier commercial profile
 */
export interface SupplierCommercialProfile {
  defaultCurrencyCode: string | null;
  paymentTermsTemplateId: string | null;
  paymentTermsTemplate: PaymentTermsTemplate | null;
}

/**
 * FX validation error
 */
export interface FXValidationError {
  field: string;
  message: string;
  details?: {
    expected: string;
    actual: string;
    tolerance: string;
  };
}

/**
 * FX validation result
 */
export interface FXValidationResult {
  isValid: boolean;
  errors: FXValidationError[];
}
