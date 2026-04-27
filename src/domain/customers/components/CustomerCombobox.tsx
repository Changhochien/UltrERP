/** Customer autocomplete combobox using Popover + Command — for invoice creation. */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Search } from "lucide-react";

import { listCustomers, createCustomer, type DuplicateInfo } from "@/lib/api/customers";
import type { CustomerSummary } from "@/domain/customers/types";
import { useToast } from "@/hooks/useToast";
import { cn } from "@/lib/utils";
import {
  customerFormSchema,
  toCustomerCreatePayload,
  type CustomerFormValues,
} from "@/lib/schemas/customer.schema";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { QuickEntryDialog } from "@/components/ui/QuickEntryDialog";
import { Spinner } from "@/components/ui/Spinner";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";

interface CustomerComboboxProps {
  value: string;
  onChange: (customerId: string) => void;
  onClear?: () => void;
  onCustomersLoaded?: (customers: CustomerSummary[]) => void;
  /** Label shown on the trigger button when no value is selected. */
  placeholder?: string;
  /** Label shown inside the search input (defaults to placeholder). */
  searchPlaceholder?: string;
  disabled?: boolean;
}

const EMPTY_CREATE_FORM: CustomerFormValues = {
  company_name: "",
  business_number: "",
  contact_phone: "",
  billing_address: "",
  contact_name: "",
  contact_email: "",
  credit_limit: "",
  default_currency_code: "",
  payment_terms_template_id: "",
};

export function CustomerCombobox({
  value,
  onChange,
  onClear,
  onCustomersLoaded,
  placeholder = "Search customer by name or BAN…",
  searchPlaceholder,
  disabled,
}: CustomerComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createForm, setCreateForm] = useState<CustomerFormValues>(EMPTY_CREATE_FORM);
  const [createError, setCreateError] = useState<string | null>(null);
  const [duplicateMatch, setDuplicateMatch] = useState<DuplicateInfo | null>(null);
  const [creating, setCreating] = useState(false);
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const toast = useToast();

  const loadCustomers = useCallback(
    (q: string) => {
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);
      listCustomers({
        status: "active",
        q: q || undefined,
        page_size: q ? 50 : 200,
      })
        .then((response) => {
          if (!controller.signal.aborted) {
            setCustomers(response.items);
            if (!q) onCustomersLoaded?.(response.items);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        });
      return controller;
    },
    [onCustomersLoaded],
  );

  // Load customers on popover open, or re-load with query when query changes (debounced)
  useEffect(() => {
    if (!open) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (query.trim().length === 0) {
      // No query — load all active customers
      loadCustomers("");
      return () => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        abortRef.current?.abort();
      };
    }

    // Debounce server-side search
    debounceRef.current = setTimeout(() => {
      loadCustomers(query);
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      abortRef.current?.abort();
    };
  }, [open, query, loadCustomers]);

  // If selected customer is not in the loaded set, fetch them
  useEffect(() => {
    if (!value || customers.some((c) => c.id === value)) return;
    listCustomers({ q: undefined, status: "active", page_size: 500 }).then((r) => {
      const match = r.items.find((c) => c.id === value);
      if (match) {
        setCustomers((prev) => {
          if (prev.some((c) => c.id === value)) return prev;
          return [...prev, match];
        });
      }
    });
  }, [value, customers]);

  const filtered = useMemo(
    () =>
      customers.filter(
        (c) =>
          c.company_name.toLowerCase().includes(query.toLowerCase()) ||
          c.normalized_business_number.includes(query),
      ),
    [customers, query],
  );
  const createValidation = useMemo(() => customerFormSchema.safeParse(createForm), [createForm]);
  const createFieldErrors = createValidation.success
    ? {}
    : createValidation.error.flatten().fieldErrors;
  const createButtonDisabled =
    creating ||
    !createForm.company_name.trim() ||
    !createForm.business_number.trim() ||
    !createForm.contact_phone.trim() ||
    !createForm.contact_name.trim() ||
    !createForm.contact_email.trim() ||
    !createValidation.success ||
    duplicateMatch !== null;

  const selectedCustomer = customers.find((c) => c.id === value);

  function handleSelect(customerId: string) {
    onChange(customerId);
    setOpen(false);
    setQuery("");
  }

  function resetCreateForm() {
    setCreateForm(EMPTY_CREATE_FORM);
    setCreateError(null);
    setDuplicateMatch(null);
  }

  function handleCreateDialogChange(nextOpen: boolean) {
    if (creating) {
      return;
    }

    setCreateDialogOpen(nextOpen);
    if (!nextOpen) {
      resetCreateForm();
    }
  }

  function openCreateDialog() {
    setOpen(false);
    setCreateError(null);
    setDuplicateMatch(null);
    setCreateForm((current) => (
      current.company_name.trim()
        ? current
        : { ...current, company_name: query.trim() }
    ));
    setCreateDialogOpen(true);
  }

  async function handleCreateSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreateError(null);
    setDuplicateMatch(null);
    if (!createValidation.success) {
      return;
    }

    const payload = toCustomerCreatePayload(createValidation.data);
    setCreating(true);

    try {
      const result = await createCustomer(payload);

      if (result.ok) {
        const createdCustomer: CustomerSummary = {
          id: result.data.id,
          company_name: result.data.company_name,
          normalized_business_number: result.data.normalized_business_number,
          contact_phone: result.data.contact_phone,
          status: result.data.status,
        };

        setCustomers((previous) => {
          const nextCustomers = [createdCustomer, ...previous.filter((customer) => customer.id !== createdCustomer.id)];
          onCustomersLoaded?.(nextCustomers);
          return nextCustomers;
        });
        onChange(result.data.id);
        setQuery("");
        setOpen(false);
        setCreateDialogOpen(false);
        resetCreateForm();
        toast.success("Customer created", `${result.data.company_name} is now selected.`);
        return;
      }

      if (result.duplicate) {
        setDuplicateMatch(result.duplicate);
        setCreateError(
          `A customer with business number "${result.duplicate.normalized_business_number}" already exists.`,
        );
        toast.warning("Customer already exists", result.duplicate.existing_customer_name);
        return;
      }

      const message = result.errors[0]?.message ?? "Failed to create customer";
      setCreateError(message);
      toast.error("Failed to create customer", message);
    } finally {
      setCreating(false);
    }
  }

  function handleUseExistingCustomer() {
    if (!duplicateMatch) {
      return;
    }

    onChange(duplicateMatch.existing_customer_id);
    setQuery("");
    setOpen(false);
    setCreateDialogOpen(false);
    toast.info("Existing customer selected", duplicateMatch.existing_customer_name);
    resetCreateForm();
  }

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <div className="relative">
          <PopoverTrigger
            render={
              <Button
                type="button"
                variant="outline"
                role="combobox"
                aria-expanded={open}
                disabled={disabled}
                className={cn(
                  "w-full justify-start pr-9 text-left font-normal",
                  !selectedCustomer && "text-muted-foreground",
                )}
              />
            }
          >
            {selectedCustomer ? (
              <span className="truncate flex-1">
                {selectedCustomer.company_name} ({selectedCustomer.normalized_business_number})
              </span>
            ) : (
              <span className="truncate flex-1">{placeholder}</span>
            )}
          </PopoverTrigger>
          {selectedCustomer && onClear ? (
            <button
              type="button"
              onClick={onClear}
              className="absolute right-2 top-1/2 inline-flex size-5 -translate-y-1/2 items-center justify-center rounded-sm text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              aria-label="Clear customer filter"
            >
              ×
            </button>
          ) : (
            <Search className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 shrink-0 opacity-50" />
          )}
        </div>
        <PopoverContent className="w-[24rem] p-0" align="start">
          <Command shouldFilter={false}>
            <CommandInput placeholder={searchPlaceholder ?? placeholder} value={query} onValueChange={setQuery} />
            <CommandList>
              {loading ? (
                <div className="flex items-center justify-center gap-2 py-6 text-center text-sm text-muted-foreground" aria-busy="true">
                  <Spinner size="sm" className="text-muted-foreground" />
                  <span>{query ? "Searching…" : "Loading customers…"}</span>
                </div>
              ) : (
                <>
                  <CommandEmpty>
                    No customers match your search.
                  </CommandEmpty>
                  {filtered.length === 0 && query.trim().length > 0 && (
                    <CommandGroup>
                      <CommandItem onSelect={openCreateDialog}>
                        <div className="flex items-center gap-2">
                          <span>Create new customer</span>
                        </div>
                      </CommandItem>
                    </CommandGroup>
                  )}
                  {filtered.length > 0 && (
                    <CommandGroup>
                      {filtered.map((customer) => (
                        <CommandItem
                          key={customer.id}
                          value={customer.id}
                          onSelect={() => handleSelect(customer.id)}
                        >
                          <div className="flex flex-col gap-0.5">
                            <span className="font-medium">{customer.company_name}</span>
                            <span className="text-xs text-muted-foreground">
                              {customer.normalized_business_number} · {customer.contact_phone}
                            </span>
                          </div>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  )}
                </>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      <QuickEntryDialog
        open={createDialogOpen}
        onOpenChange={handleCreateDialogChange}
        title="Create new customer"
        description="Add the customer here and select it without leaving the current form."
        size="lg"
        busy={creating}
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4" noValidate>
          {duplicateMatch ? (
            <div className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-foreground" role="alert">
              <p>
                A customer with business number "{duplicateMatch.normalized_business_number}" already exists:
                {" "}
                <strong>{duplicateMatch.existing_customer_name}</strong>
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button type="button" size="sm" onClick={handleUseExistingCustomer}>
                  Use existing customer
                </Button>
                <Button type="button" size="sm" variant="outline" onClick={() => setDuplicateMatch(null)}>
                  Continue editing
                </Button>
              </div>
            </div>
          ) : null}
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              placeholder="Company name *"
              value={createForm.company_name}
              onChange={(e) => setCreateForm((form) => ({ ...form, company_name: e.target.value }))}
              disabled={creating}
            />
            <Input
              placeholder="Business number *"
              value={createForm.business_number}
              onChange={(e) => setCreateForm((form) => ({ ...form, business_number: e.target.value }))}
              disabled={creating}
            />
            <Input
              placeholder="Contact phone *"
              value={createForm.contact_phone}
              onChange={(e) => setCreateForm((form) => ({ ...form, contact_phone: e.target.value }))}
              disabled={creating}
            />
            <Input
              placeholder="Contact name *"
              value={createForm.contact_name}
              onChange={(e) => setCreateForm((form) => ({ ...form, contact_name: e.target.value }))}
              disabled={creating}
            />
            <Input
              placeholder="Contact email *"
              value={createForm.contact_email}
              onChange={(e) => setCreateForm((form) => ({ ...form, contact_email: e.target.value }))}
              disabled={creating}
            />
            <Input
              placeholder="Credit limit (optional)"
              value={createForm.credit_limit}
              onChange={(e) => setCreateForm((form) => ({ ...form, credit_limit: e.target.value }))}
              disabled={creating}
            />
          </div>
          <Input
            placeholder="Billing address"
            value={createForm.billing_address}
            onChange={(e) => setCreateForm((form) => ({ ...form, billing_address: e.target.value }))}
            disabled={creating}
          />
          {(createFieldErrors.company_name || createFieldErrors.business_number || createFieldErrors.contact_phone || createFieldErrors.contact_name || createFieldErrors.contact_email || createFieldErrors.credit_limit) && (
            <div className="space-y-1 text-xs text-destructive" role="alert" aria-live="polite">
              {createFieldErrors.company_name?.[0] ? <p>{createFieldErrors.company_name[0]}</p> : null}
              {createFieldErrors.business_number?.[0] ? <p>{createFieldErrors.business_number[0]}</p> : null}
              {createFieldErrors.contact_phone?.[0] ? <p>{createFieldErrors.contact_phone[0]}</p> : null}
              {createFieldErrors.contact_name?.[0] ? <p>{createFieldErrors.contact_name[0]}</p> : null}
              {createFieldErrors.contact_email?.[0] ? <p>{createFieldErrors.contact_email[0]}</p> : null}
              {createFieldErrors.credit_limit?.[0] ? <p>{createFieldErrors.credit_limit[0]}</p> : null}
            </div>
          )}
          {createError ? <p className="text-xs text-destructive">{createError}</p> : null}
          <div className="flex justify-end gap-2">
            <Button type="button" size="sm" variant="outline" onClick={() => handleCreateDialogChange(false)} disabled={creating}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={createButtonDisabled}>
              {creating ? (
                <>
                  <Spinner size="sm" className="text-current" />
                  Creating…
                </>
              ) : (
                "Create"
              )}
            </Button>
          </div>
        </form>
      </QuickEntryDialog>
    </>
  );
}
