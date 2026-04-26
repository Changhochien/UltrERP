/**
 * API client for accounting domain (Epic 26).
 */

import { apiFetch } from "../apiFetch";

import type {
  Account,
  AccountListResponse,
  AccountTreeResponse,
  CreateAccountRequest,
  CreateFiscalYearRequest,
  CreateJournalEntryRequest,
  CreateJournalEntryLineRequest,
  FiscalYear,
  FiscalYearListResponse,
  GLEntryListResponse,
  JournalEntry,
  JournalEntryDetail,
  JournalEntryListResponse,
  JournalEntryReverseResponse,
  JournalEntrySubmitResponse,
  LedgerSummaryResponse,
  StarterChartProfile,
  UpdateAccountRequest,
  UpdateFiscalYearRequest,
  UpdateJournalEntryRequest,
} from "@/domain/accounting/types";

const API_BASE = "/api/v1";

async function fetchApi<T>(
  path: string,
  options?: RequestInit & { signal?: AbortSignal }
): Promise<T> {
  const response = await apiFetch(`${API_BASE}${path}`, options);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw error;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ============================================================
// Account API Functions
// ============================================================

/**
 * Get full account tree for the tenant.
 */
export async function fetchAccountTree(includeDisabled = false): Promise<AccountTreeResponse> {
  return fetchApi<AccountTreeResponse>(
    `/accounting/accounts?include_disabled=${includeDisabled}`
  );
}

/**
 * List accounts with pagination.
 */
export async function fetchAccounts(
  page = 1,
  pageSize = 50,
  options?: {
    rootType?: string;
    includeDisabled?: boolean;
  }
): Promise<AccountListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  if (options?.rootType) {
    params.set("root_type", options.rootType);
  }
  if (options?.includeDisabled) {
    params.set("include_disabled", "true");
  }

  return fetchApi<AccountListResponse>(`/accounting/accounts/list?${params}`);
}

/**
 * Get a single account by ID.
 */
export async function fetchAccount(accountId: string): Promise<Account> {
  return fetchApi<Account>(`/accounting/accounts/${accountId}`);
}

/**
 * Create a new account.
 */
export async function createAccount(data: CreateAccountRequest): Promise<Account> {
  return fetchApi<Account>("/accounting/accounts", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * Update an existing account.
 */
export async function updateAccount(
  accountId: string,
  data: UpdateAccountRequest
): Promise<Account> {
  return fetchApi<Account>(`/accounting/accounts/${accountId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

/**
 * Freeze an account (rejects postings).
 */
export async function freezeAccount(accountId: string): Promise<Account> {
  return fetchApi<Account>(`/accounting/accounts/${accountId}/freeze`, {
    method: "POST",
  });
}

/**
 * Unfreeze an account (allows postings).
 */
export async function unfreezeAccount(accountId: string): Promise<Account> {
  return fetchApi<Account>(`/accounting/accounts/${accountId}/unfreeze`, {
    method: "POST",
  });
}

/**
 * Disable an account (hides from selection).
 */
export async function disableAccount(accountId: string): Promise<Account> {
  return fetchApi<Account>(`/accounting/accounts/${accountId}/disable`, {
    method: "POST",
  });
}

/**
 * Delete an account (only if no children).
 */
export async function deleteAccount(accountId: string): Promise<void> {
  return fetchApi<void>(`/accounting/accounts/${accountId}`, {
    method: "DELETE",
  });
}

/**
 * Seed the standard starter chart.
 */
export async function seedStarterChart(): Promise<AccountTreeResponse> {
  return fetchApi<AccountTreeResponse>("/accounting/accounts/seed", {
    method: "POST",
  });
}

/**
 * Get available starter chart profiles.
 */
export async function fetchStarterProfiles(): Promise<StarterChartProfile[]> {
  return fetchApi<StarterChartProfile[]>("/accounting/accounts/starter-profiles");
}

// ============================================================
// Fiscal Year API Functions
// ============================================================

/**
 * List fiscal years with pagination.
 */
export async function fetchFiscalYears(
  page = 1,
  pageSize = 50
): Promise<FiscalYearListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  return fetchApi<FiscalYearListResponse>(`/accounting/fiscal-years?${params}`);
}

/**
 * Get a single fiscal year by ID.
 */
export async function fetchFiscalYear(fiscalYearId: string): Promise<FiscalYear> {
  return fetchApi<FiscalYear>(`/accounting/fiscal-years/${fiscalYearId}`);
}

/**
 * Create a new fiscal year.
 */
export async function createFiscalYear(data: CreateFiscalYearRequest): Promise<FiscalYear> {
  return fetchApi<FiscalYear>("/accounting/fiscal-years", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * Update an existing fiscal year.
 */
export async function updateFiscalYear(
  fiscalYearId: string,
  data: UpdateFiscalYearRequest
): Promise<FiscalYear> {
  return fetchApi<FiscalYear>(`/accounting/fiscal-years/${fiscalYearId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

/**
 * Close a fiscal year (rejects postings).
 */
export async function closeFiscalYear(
  fiscalYearId: string,
  closureNotes?: string
): Promise<FiscalYear> {
  return fetchApi<FiscalYear>(`/accounting/fiscal-years/${fiscalYearId}/close`, {
    method: "POST",
    body: JSON.stringify({ closure_notes: closureNotes }),
  });
}

/**
 * Reopen a closed fiscal year.
 */
export async function reopenFiscalYear(fiscalYearId: string): Promise<FiscalYear> {
  return fetchApi<FiscalYear>(`/accounting/fiscal-years/${fiscalYearId}/reopen`, {
    method: "POST",
  });
}

/**
 * Get the fiscal year containing a given date.
 */
export async function fetchFiscalYearForDate(date: string): Promise<FiscalYear> {
  return fetchApi<FiscalYear>(`/accounting/fiscal-years/lookup/${date}`);
}

/**
 * Get all open fiscal years.
 */
export async function fetchOpenFiscalYears(): Promise<FiscalYear[]> {
  return fetchApi<FiscalYear[]>("/accounting/fiscal-years/open");
}

// ============================================================
// Journal Entry API Functions
// ============================================================

/**
 * List journal entries with pagination and filters.
 */
export async function fetchJournalEntries(options?: {
  page?: number;
  pageSize?: number;
  status?: string;
  voucherType?: string;
  fromDate?: string;
  toDate?: string;
}): Promise<JournalEntryListResponse> {
  const params = new URLSearchParams({
    page: String(options?.page ?? 1),
    page_size: String(options?.pageSize ?? 50),
  });

  if (options?.status) {
    params.set("status", options.status);
  }
  if (options?.voucherType) {
    params.set("voucher_type", options.voucherType);
  }
  if (options?.fromDate) {
    params.set("from_date", options.fromDate);
  }
  if (options?.toDate) {
    params.set("to_date", options.toDate);
  }

  return fetchApi<JournalEntryListResponse>(
    `/accounting/journal-entries?${params}`
  );
}

/**
 * Get a journal entry with full details.
 */
export async function fetchJournalEntry(journalEntryId: string): Promise<JournalEntryDetail> {
  return fetchApi<JournalEntryDetail>(
    `/accounting/journal-entries/${journalEntryId}`
  );
}

/**
 * Create a new journal entry.
 */
export async function createJournalEntry(
  data: CreateJournalEntryRequest
): Promise<JournalEntry> {
  return fetchApi<JournalEntry>("/accounting/journal-entries", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * Update a draft journal entry.
 */
export async function updateJournalEntry(
  journalEntryId: string,
  data: UpdateJournalEntryRequest
): Promise<JournalEntry> {
  return fetchApi<JournalEntry>(
    `/accounting/journal-entries/${journalEntryId}`,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    }
  );
}

/**
 * Submit a journal entry and create GL entries.
 */
export async function submitJournalEntry(
  journalEntryId: string
): Promise<JournalEntrySubmitResponse> {
  return fetchApi<JournalEntrySubmitResponse>(
    `/accounting/journal-entries/${journalEntryId}/submit`,
    { method: "POST" }
  );
}

/**
 * Reverse a submitted journal entry.
 */
export async function reverseJournalEntry(
  journalEntryId: string,
  options?: {
    reversalDate?: string;
    cancelReason?: string;
  }
): Promise<JournalEntryReverseResponse> {
  const params = new URLSearchParams();
  if (options?.reversalDate) {
    params.set("reversal_date", options.reversalDate);
  }
  if (options?.cancelReason) {
    params.set("cancel_reason", options.cancelReason);
  }

  return fetchApi<JournalEntryReverseResponse>(
    `/accounting/journal-entries/${journalEntryId}/reverse?${params}`,
    { method: "POST" }
  );
}

/**
 * Add a line to a draft journal entry.
 */
export async function addJournalEntryLine(
  journalEntryId: string,
  data: CreateJournalEntryLineRequest
): Promise<CreateJournalEntryLineRequest> {
  return fetchApi<CreateJournalEntryLineRequest>(
    `/accounting/journal-entries/${journalEntryId}/lines`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

/**
 * Remove a line from a draft journal entry.
 */
export async function removeJournalEntryLine(
  journalEntryId: string,
  lineId: string
): Promise<void> {
  return fetchApi<void>(
    `/accounting/journal-entries/${journalEntryId}/lines/${lineId}`,
    { method: "DELETE" }
  );
}

// ============================================================
// General Ledger API Functions
// ============================================================

/**
 * Get general ledger entries with filters.
 */
export async function fetchGeneralLedger(options?: {
  page?: number;
  pageSize?: number;
  accountId?: string;
  fromDate?: string;
  toDate?: string;
  voucherType?: string;
  voucherNumber?: string;
  includeReversed?: boolean;
}): Promise<GLEntryListResponse> {
  const params = new URLSearchParams({
    page: String(options?.page ?? 1),
    page_size: String(options?.pageSize ?? 50),
  });

  if (options?.accountId) {
    params.set("account_id", options.accountId);
  }
  if (options?.fromDate) {
    params.set("from_date", options.fromDate);
  }
  if (options?.toDate) {
    params.set("to_date", options.toDate);
  }
  if (options?.voucherType) {
    params.set("voucher_type", options.voucherType);
  }
  if (options?.voucherNumber) {
    params.set("voucher_number", options.voucherNumber);
  }
  if (options?.includeReversed) {
    params.set("include_reversed", "true");
  }

  return fetchApi<GLEntryListResponse>(
    `/accounting/general-ledger?${params}`
  );
}

/**
 * Get account ledger with opening balance, entries, and closing balance.
 */
export async function fetchAccountLedger(
  accountId: string,
  options?: {
    fromDate?: string;
    toDate?: string;
  }
): Promise<LedgerSummaryResponse> {
  const params = new URLSearchParams();

  if (options?.fromDate) {
    params.set("from_date", options.fromDate);
  }
  if (options?.toDate) {
    params.set("to_date", options.toDate);
  }

  return fetchApi<LedgerSummaryResponse>(
    `/accounting/accounts/${accountId}/ledger?${params}`
  );
}
