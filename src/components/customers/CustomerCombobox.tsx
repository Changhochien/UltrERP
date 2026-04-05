/** Customer autocomplete combobox using Popover + Command — for invoice creation. */

import { useEffect, useRef, useState } from "react";
import { Search } from "lucide-react";

import { listCustomers } from "../../lib/api/customers";
import type { CustomerSummary } from "../../domain/customers/types";
import { cn } from "../../lib/utils";
import { Button } from "../ui/button";
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
  placeholder?: string;
  disabled?: boolean;
}

export function CustomerCombobox({
  value,
  onChange,
  placeholder = "Search customer by name or BAN…",
  disabled,
}: CustomerComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Load all active customers when the popover opens
  useEffect(() => {
    if (!open) return;

    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);

    listCustomers({ status: "active", page_size: 200 })
      .then((response) => {
        if (!controller.signal.aborted) {
          setCustomers(response.items);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [open]);

  const filtered =
    query.trim().length === 0
      ? customers
      : customers.filter(
          (c) =>
            c.company_name.toLowerCase().includes(query.toLowerCase()) ||
            c.normalized_business_number.includes(query),
        );

  const selectedCustomer = customers.find((c) => c.id === value);

  function handleSelect(customerId: string) {
    onChange(customerId);
    setOpen(false);
    setQuery("");
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
          <span className="truncate">
            {selectedCustomer.company_name} ({selectedCustomer.normalized_business_number})
          </span>
        ) : (
          <span className="truncate">{placeholder}</span>
        )}
        <Search className="ml-auto size-4 shrink-0 opacity-50" />
      </PopoverTrigger>
      <PopoverContent className="w-[24rem] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput placeholder={placeholder} value={query} onValueChange={setQuery} />
          <CommandList>
            {loading ? (
              <div className="py-6 text-center text-sm text-muted-foreground">
                Loading customers…
              </div>
            ) : (
              <>
                <CommandEmpty>
                  {query.length >= 3
                    ? "No customers match your search."
                    : "Type at least 3 characters to search."}
                </CommandEmpty>
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
  );
}
