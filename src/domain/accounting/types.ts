/**
 * TypeScript types for accounting domain (Epic 26).
 */

// ============================================================
// Account Types
// ============================================================

export type AccountRootType = "Asset" | "Liability" | "Equity" | "Income" | "Expense";

export type AccountReportType = "Balance Sheet" | "Profit and Loss";

export type AccountType =
  | "Root Asset" | "Bank" | "Cash" | "Receivable" | "Inventory"
  | "Current Asset" | "Fixed Asset" | "Non-Current Asset" | "Prepayment" | "Tax Asset"
  | "Root Liability" | "Payable" | "Credit Card" | "Current Liability"
  | "Non-Current Liability" | "Tax Liability"
  | "Root Equity" | "Retained Earnings" | "Shareholders Equity"
  | "Root Income" | "Sales" | "Service Revenue" | "Other Income"
  | "Root Expense" | "Cost of Goods Sold" | "Expense" | "Depreciation" | "Tax Expense";

export interface Account {
  id: string;
  tenant_id: string;
  parent_id: string | null;
  parent_number: string | null;
  account_number: string;
  account_name: string;
  root_type: AccountRootType;
  report_type: AccountReportType;
  account_type: AccountType;
  is_group: boolean;
  is_frozen: boolean;
  is_disabled: boolean;
  sort_order: number;
  currency_code: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccountTreeNode extends Account {
  children: AccountTreeNode[];
}

export interface AccountListResponse {
  items: Account[];
  total: number;
  page: number;
  page_size: number;
}

export interface AccountTreeResponse {
  roots: AccountTreeNode[];
  total_accounts: number;
}

export interface CreateAccountRequest {
  account_number: string;
  account_name: string;
  root_type: AccountRootType;
  account_type: AccountType;
  is_group?: boolean;
  is_frozen?: boolean;
  is_disabled?: boolean;
  sort_order?: number;
  currency_code?: string | null;
  parent_id?: string | null;
}

export interface UpdateAccountRequest {
  account_number?: string;
  account_name?: string;
  account_type?: AccountType;
  is_group?: boolean;
  is_frozen?: boolean;
  is_disabled?: boolean;
  sort_order?: number;
  currency_code?: string | null;
  parent_id?: string | null;
}

// ============================================================
// Fiscal Year Types
// ============================================================

export type FiscalYearStatus = "Draft" | "Open" | "Closed" | "Archived";

export interface FiscalYear {
  id: string;
  tenant_id: string;
  label: string;
  start_date: string;
  end_date: string;
  status: FiscalYearStatus;
  is_default: boolean;
  closed_at: string | null;
  closed_by: string | null;
  closure_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface FiscalYearListResponse {
  items: FiscalYear[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateFiscalYearRequest {
  label: string;
  start_date: string;
  end_date: string;
  is_default?: boolean;
}

export interface UpdateFiscalYearRequest {
  label?: string;
  start_date?: string;
  end_date?: string;
  status?: FiscalYearStatus;
  is_default?: boolean;
  closure_notes?: string | null;
}

// ============================================================
// Starter Chart Types
// ============================================================

export interface StarterAccountDefinition {
  account_number: string;
  account_name: string;
  root_type: AccountRootType;
  account_type: AccountType;
  parent_number: string | null;
  is_group: boolean;
}

export interface StarterChartProfile {
  name: string;
  description: string;
  accounts: StarterAccountDefinition[];
}

// ============================================================
// API Error Types
// ============================================================

export interface ValidationErrorItem {
  field: string;
  message: string;
}

export interface ApiError {
  detail: string | { errors: ValidationErrorItem[] };
}

// ============================================================
// Constants
// ============================================================

export const ROOT_TYPE_COLORS: Record<AccountRootType, string> = {
  Asset: "#3b82f6",    // blue
  Liability: "#ef4444", // red
  Equity: "#8b5cf6",   // purple
  Income: "#22c55e",   // green
  Expense: "#f59e0b",  // amber
};

// Alias for backward compatibility
export const ROOT_TYPE_REPORT_COLORS = ROOT_TYPE_COLORS;

export const ROOT_TYPE_LABELS: Record<AccountRootType, string> = {
  Asset: "Asset",
  Liability: "Liability",
  Equity: "Equity",
  Income: "Income",
  Expense: "Expense",
};

export const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  "Root Asset": "Root Asset",
  Bank: "Bank",
  Cash: "Cash",
  Receivable: "Receivable",
  Inventory: "Inventory",
  "Current Asset": "Current Asset",
  "Fixed Asset": "Fixed Asset",
  "Non-Current Asset": "Non-Current Asset",
  Prepayment: "Prepayment",
  "Tax Asset": "Tax Asset",
  "Root Liability": "Root Liability",
  Payable: "Payable",
  "Credit Card": "Credit Card",
  "Current Liability": "Current Liability",
  "Non-Current Liability": "Non-Current Liability",
  "Tax Liability": "Tax Liability",
  "Root Equity": "Root Equity",
  "Retained Earnings": "Retained Earnings",
  "Shareholders Equity": "Shareholders Equity",
  "Root Income": "Root Income",
  Sales: "Sales",
  "Service Revenue": "Service Revenue",
  "Other Income": "Other Income",
  "Root Expense": "Root Expense",
  "Cost of Goods Sold": "Cost of Goods Sold",
  Expense: "Expense",
  Depreciation: "Depreciation",
  "Tax Expense": "Tax Expense",
};

export const FISCAL_YEAR_STATUS_LABELS: Record<FiscalYearStatus, string> = {
  Draft: "Draft",
  Open: "Open",
  Closed: "Closed",
  Archived: "Archived",
};

export const JOURNAL_ENTRY_STATUS_LABELS: Record<JournalEntryStatus, string> = {
  Draft: "Draft",
  Submitted: "Submitted",
  Cancelled: "Cancelled",
};

export const JOURNAL_ENTRY_STATUS_COLORS: Record<JournalEntryStatus, string> = {
  Draft: "#f59e0b",     // amber
  Submitted: "#22c55e", // green
  Cancelled: "#ef4444", // red
};

export const VOUCHER_TYPE_LABELS: Record<VoucherType, string> = {
  "Journal Entry": "Journal Entry",
  "Opening Entry": "Opening Entry",
};

export const EMPTY_REASON_LABELS: Record<EmptyReason, string> = {
  no_entries_in_period: "No ledger entries in this period",
  no_accounts_configured: "No accounts configured",
  all_accounts_disabled: "All accounts are disabled",
};

// ============================================================
// Journal Entry Types
// ============================================================

export type JournalEntryStatus = "Draft" | "Submitted" | "Cancelled";
export type VoucherType = "Journal Entry" | "Opening Entry";
export type GLEntryType = "Journal Entry" | "Opening Entry";

export interface JournalEntryLine {
  id: string;
  journal_entry_id: string;
  account_id: string;
  debit: number;
  credit: number;
  remark: string | null;
  cost_center_id: string | null;
  project_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface JournalEntryLineWithAccount extends JournalEntryLine {
  account_number: string;
  account_name: string;
  account_root_type: string;
}

export interface JournalEntry {
  id: string;
  tenant_id: string;
  voucher_type: VoucherType;
  voucher_number: string;
  posting_date: string;
  reference_date: string | null;
  status: JournalEntryStatus;
  narration: string | null;
  total_debit: number;
  total_credit: number;
  reference_type: string | null;
  reference_id: string | null;
  external_reference_number: string | null;
  external_reference_date: string | null;
  reversed_by_id: string | null;
  reverses_id: string | null;
  submitted_at: string | null;
  submitted_by: string | null;
  cancelled_at: string | null;
  cancelled_by: string | null;
  cancel_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface JournalEntryDetail extends JournalEntry {
  lines: JournalEntryLineWithAccount[];
}

export interface JournalEntryListResponse {
  items: JournalEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateJournalEntryLineRequest {
  account_id: string;
  debit: number;
  credit: number;
  remark?: string | null;
  cost_center_id?: string | null;
  project_id?: string | null;
}

export interface CreateJournalEntryRequest {
  voucher_type: VoucherType;
  posting_date: string;
  reference_date?: string | null;
  narration?: string | null;
  reference_type?: string | null;
  reference_id?: string | null;
  external_reference_number?: string | null;
  external_reference_date?: string | null;
  lines: CreateJournalEntryLineRequest[];
}

export interface UpdateJournalEntryRequest {
  voucher_type?: VoucherType;
  posting_date?: string;
  reference_date?: string | null;
  narration?: string | null;
  reference_type?: string | null;
  reference_id?: string | null;
  external_reference_number?: string | null;
  external_reference_date?: string | null;
}

export interface JournalEntrySubmitResponse {
  journal_entry: JournalEntry;
  gl_entries_created: number;
  message: string;
}

export interface JournalEntryReverseResponse {
  original_entry: JournalEntry;
  reversing_entry: JournalEntry;
  gl_entries_created: number;
  message: string;
}

// ============================================================
// GL Entry Types
// ============================================================

export interface GLEntry {
  id: string;
  tenant_id: string;
  account_id: string;
  posting_date: string;
  fiscal_year: string;
  debit: number;
  credit: number;
  entry_type: GLEntryType;
  voucher_type: string;
  voucher_number: string;
  source_type: string | null;
  source_id: string | null;
  journal_entry_id: string | null;
  journal_entry_line_id: string | null;
  reversed_by_id: string | null;
  reverses_id: string | null;
  remark: string | null;
  created_at: string;
}

export interface GLEntryWithAccount extends GLEntry {
  account_number: string;
  account_name: string;
  account_root_type: string;
  account_type: string;
}

export interface GLEntryListResponse {
  items: GLEntryWithAccount[];
  total: number;
  page: number;
  page_size: number;
}

export interface LedgerAccountSummary {
  account_id: string;
  account_number: string;
  account_name: string;
  opening_balance: number;
  total_debit: number;
  total_credit: number;
  closing_balance: number;
  entries: GLEntryWithAccount[];
}

export interface LedgerSummaryResponse {
  account: Account;
  summary: LedgerAccountSummary;
}

// (Constants already defined in types.ts)

// ============================================================
// Utility Types
// ============================================================

export type AccountFormData = Omit<CreateAccountRequest, "root_type"> & {
  root_type: AccountRootType;
};

export type FiscalYearFormData = Omit<CreateFiscalYearRequest, "start_date" | "end_date"> & {
  start_date: Date;
  end_date: Date;
};

export type JournalEntryFormData = {
  voucher_type: VoucherType;
  posting_date: Date;
  reference_date?: Date | null;
  narration?: string;
  lines: Array<{
    account_id: string;
    debit: number;
    credit: number;
    remark?: string;
  }>;
};

// ============================================================
// Financial Report Types (Epic 26.3)
// ============================================================

export type EmptyReason =
  | "no_entries_in_period"
  | "no_accounts_configured"
  | "all_accounts_disabled";

export interface ReportMetadata {
  report_type: string;
  as_of_date: string | null;
  from_date: string | null;
  to_date: string | null;
  fiscal_year: string | null;
  empty_reason: EmptyReason | null;
  generated_at: string | null;
}

export interface ProfitAndLossRow {
  account_id: string;
  account_number: string;
  account_name: string;
  amount: string;
  is_group: boolean;
  indent_level: number;
  is_subtotal: boolean;
}

export interface ProfitAndLossResponse {
  metadata: ReportMetadata;
  income_rows: ProfitAndLossRow[];
  income_total: string;
  expense_rows: ProfitAndLossRow[];
  expense_total: string;
  net_profit: string;
}

export interface BalanceSheetRow {
  account_id: string;
  account_number: string;
  account_name: string;
  amount: string;
  is_group: boolean;
  indent_level: number;
  is_subtotal: boolean;
}

export interface BalanceSheetResponse {
  metadata: ReportMetadata;
  asset_rows: BalanceSheetRow[];
  total_assets: string;
  liability_rows: BalanceSheetRow[];
  total_liabilities: string;
  equity_rows: BalanceSheetRow[];
  total_equity: string;
  total_liabilities_and_equity: string;
}

export interface TrialBalanceRow {
  account_id: string;
  account_number: string;
  account_name: string;
  root_type: string;
  debit: string;
  credit: string;
}

export interface TrialBalanceResponse {
  metadata: ReportMetadata;
  rows: TrialBalanceRow[];
  total_debit: string;
  total_credit: string;
  is_balanced: boolean;
}
