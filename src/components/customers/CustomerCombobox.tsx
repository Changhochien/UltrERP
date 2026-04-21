/** Customer autocomplete combobox using Popover + Command — for invoice creation. */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Search } from "lucide-react";

import { listCustomers, createCustomer } from "../../lib/api/customers";
import type { CustomerSummary } from "../../domain/customers/types";
import { cn } from "../../lib/utils";
import {
  customerFormSchema,
  toCustomerCreatePayload,
  type CustomerFormValues,
} from "../../lib/schemas/customer.schema";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "../ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "../ui/command";

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
  const [showCreatePanel, setShowCreatePanel] = useState(false);
  const [createForm, setCreateForm] = useState<CustomerFormValues>({
    company_name: "",
    business_number: "",
    contact_phone: "",
    billing_address: "",
    contact_name: "",
    contact_email: "",
    credit_limit: "",
  });
  const [createError, setCreateError] = useState<string | null>(null);
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  const selectedCustomer = customers.find((c) => c.id === value);

  function handleSelect(customerId: string) {
    onChange(customerId);
    setOpen(false);
    setQuery("");
  }

  async function handleCreateSubmit() {
    setCreateError(null);
    if (!createValidation.success) {
      return;
    }

    const payload = toCustomerCreatePayload(createValidation.data);
    const result = await createCustomer(payload);
    if (result.ok) {
      onChange(result.data.id);
      setOpen(false);
      setQuery("");
      setShowCreatePanel(false);
      setCreateForm({ company_name: "", business_number: "", contact_phone: "", billing_address: "", contact_name: "", contact_email: "", credit_limit: "" });
    } else if (result.duplicate) {
      const confirmed = window.confirm(
        `A customer with business number "${result.duplicate.normalized_business_number}" already exists: "${result.duplicate.existing_customer_name}". Use existing customer?`,
      );
      if (confirmed) {
        onChange(result.duplicate.existing_customer_id);
        setOpen(false);
        setQuery("");
        setShowCreatePanel(false);
      }
    } else if (result.errors) {
      setCreateError(result.errors[0]?.message ?? "Failed to create customer");
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <Button
            type="button"
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled}
            className={cn(
              "w-full justify-start text-left font-normal",
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
        {selectedCustomer && onClear ? (
          <span
            role="button"
            tabIndex={0}
            onClick={(e) => {
              e.stopPropagation();
              onClear();
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.stopPropagation();
                onClear();
              }
            }}
            className="ml-1 rounded-sm opacity-70 hover:opacity-100 focus:outline-none cursor-pointer"
            aria-label="Clear customer filter"
          >
            ×
          </span>
        ) : (
          <Search className="ml-1 size-4 shrink-0 opacity-50" />
        )}
      </PopoverTrigger>
      <PopoverContent className="w-[24rem] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput placeholder={searchPlaceholder ?? placeholder} value={query} onValueChange={setQuery} />
          <CommandList>
            {loading ? (
              <div className="py-6 text-center text-sm text-muted-foreground">
                {query ? "Searching…" : "Loading customers…"}
              </div>
            ) : (
              <>
                <CommandEmpty>
                  No customers match your search.
                </CommandEmpty>
                {filtered.length === 0 && query.trim().length > 0 && (
                  <CommandGroup>
                    <CommandItem onSelect={() => setShowCreatePanel(true)}>
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
          {showCreatePanel && (
            <div className="border-t p-3 space-y-3">
              <p className="text-sm font-medium text-foreground">Create new customer</p>
              <div className="space-y-2">
                <Input
                  placeholder="Company name *"
                  value={createForm.company_name}
                  onChange={(e) => setCreateForm((f) => ({ ...f, company_name: e.target.value }))}
                />
                <Input
                  placeholder="Business number *"
                  value={createForm.business_number}
                  onChange={(e) => setCreateForm((f) => ({ ...f, business_number: e.target.value }))}
                />
                <Input
                  placeholder="Contact phone *"
                  value={createForm.contact_phone}
                  onChange={(e) => setCreateForm((f) => ({ ...f, contact_phone: e.target.value }))}
                />
                <Input
                  placeholder="Billing address"
                  value={createForm.billing_address}
                  onChange={(e) => setCreateForm((f) => ({ ...f, billing_address: e.target.value }))}
                />
                <Input
                  placeholder="Contact name *"
                  value={createForm.contact_name}
                  onChange={(e) => setCreateForm((f) => ({ ...f, contact_name: e.target.value }))}
                />
                <Input
                  placeholder="Contact email *"
                  value={createForm.contact_email}
                  onChange={(e) => setCreateForm((f) => ({ ...f, contact_email: e.target.value }))}
                />
                <Input
                  placeholder="Credit limit (optional)"
                  value={createForm.credit_limit}
                  onChange={(e) => setCreateForm((f) => ({ ...f, credit_limit: e.target.value }))}
                />
              </div>
              {(createFieldErrors.company_name || createFieldErrors.business_number || createFieldErrors.contact_phone || createFieldErrors.contact_name || createFieldErrors.contact_email || createFieldErrors.credit_limit) && (
                <div className="space-y-1 text-xs text-destructive">
                  {createFieldErrors.company_name?.[0] ? <p>{createFieldErrors.company_name[0]}</p> : null}
                  {createFieldErrors.business_number?.[0] ? <p>{createFieldErrors.business_number[0]}</p> : null}
                  {createFieldErrors.contact_phone?.[0] ? <p>{createFieldErrors.contact_phone[0]}</p> : null}
                  {createFieldErrors.contact_name?.[0] ? <p>{createFieldErrors.contact_name[0]}</p> : null}
                  {createFieldErrors.contact_email?.[0] ? <p>{createFieldErrors.contact_email[0]}</p> : null}
                  {createFieldErrors.credit_limit?.[0] ? <p>{createFieldErrors.credit_limit[0]}</p> : null}
                </div>
              )}
              {createError && (
                <p className="text-xs text-destructive">{createError}</p>
              )}
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={handleCreateSubmit}
                  disabled={!createForm.company_name.trim() || !createForm.business_number.trim() || !createForm.contact_phone.trim()}
                  disabled={
                    !createForm.company_name.trim() ||
                    !createForm.business_number.trim() ||
                    !createForm.contact_phone.trim() ||
                    !createForm.contact_name.trim() ||
                    !createForm.contact_email.trim() ||
                    !createValidation.success
                  }
                >
                  Create
                </Button>
                <Button size="sm" variant="outline" onClick={() => setShowCreatePanel(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </Command>
      </PopoverContent>
    </Popover>
  );
}
