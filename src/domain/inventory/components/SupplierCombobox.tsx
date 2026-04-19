import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Search } from "lucide-react";

import { fetchSuppliers } from "../../../lib/api/inventory";
import { cn } from "../../../lib/utils";
import type { Supplier } from "../types";
import { Button } from "../../../components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "../../../components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "../../../components/ui/command";

interface SupplierComboboxProps {
  value: string;
  onChange: (supplierId: string) => void;
  onClear?: () => void;
  placeholder?: string;
  disabled?: boolean;
  activeOnly?: boolean;
  inputId?: string;
  ariaLabel?: string;
  ariaLabelledBy?: string;
}

export function SupplierCombobox({
  value,
  onChange,
  onClear,
  placeholder = "Search supplier…",
  disabled,
  activeOnly = true,
  inputId,
  ariaLabel,
  ariaLabelledBy,
}: SupplierComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [selectedSupplier, setSelectedSupplier] = useState<Supplier | null>(null);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadSuppliers = useCallback(
    async (nextQuery: string) => {
      abortRef.current = false;
      setLoading(true);
      const response = await fetchSuppliers({
        q: nextQuery.trim() || undefined,
        activeOnly,
        limit: 50,
      });

      if (abortRef.current) {
        return;
      }

      if (response.ok) {
        setSuppliers(response.data.items);
        if (value) {
          const match = response.data.items.find((supplier) => supplier.id === value);
          if (match) {
            setSelectedSupplier(match);
          }
        }
      } else {
        setSuppliers([]);
      }
      setLoading(false);
    },
    [activeOnly, value],
  );

  useEffect(() => {
    if (!open) {
      return;
    }

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (query.trim().length === 0) {
      void loadSuppliers("");
      return () => {
        abortRef.current = true;
      };
    }

    debounceRef.current = setTimeout(() => {
      void loadSuppliers(query);
    }, 250);

    return () => {
      abortRef.current = true;
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [loadSuppliers, open, query]);

  useEffect(() => {
    if (!value) {
      setSelectedSupplier(null);
      return;
    }

    const match = suppliers.find((supplier) => supplier.id === value);
    if (match) {
      setSelectedSupplier(match);
    }
  }, [suppliers, value]);

  useEffect(() => {
    if (!open) {
      setQuery("");
    }
  }, [open]);

  useEffect(() => {
    return () => {
      abortRef.current = true;
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  const filteredSuppliers = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return suppliers;
    }
    return suppliers.filter((supplier) => supplier.name.toLowerCase().includes(normalizedQuery));
  }, [query, suppliers]);

  function handleSelect(supplier: Supplier) {
    setSelectedSupplier(supplier);
    onChange(supplier.id);
    setOpen(false);
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <Button
            id={inputId}
            type="button"
            variant="outline"
            role="combobox"
            aria-expanded={open}
            aria-label={ariaLabel}
            aria-labelledby={ariaLabelledBy}
            disabled={disabled}
            className={cn(
              "w-full justify-start text-left font-normal",
              !selectedSupplier && "text-muted-foreground",
            )}
          />
        }
      >
        {selectedSupplier ? (
          <span className="truncate flex-1">{selectedSupplier.name}</span>
        ) : (
          <span className="truncate flex-1">{placeholder}</span>
        )}
        {selectedSupplier && onClear ? (
          <span
            role="button"
            tabIndex={0}
            onClick={(event) => {
              event.stopPropagation();
              setSelectedSupplier(null);
              onClear();
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.stopPropagation();
                setSelectedSupplier(null);
                onClear();
              }
            }}
            className="ml-1 cursor-pointer rounded-sm opacity-70 hover:opacity-100 focus:outline-none"
            aria-label="Clear supplier"
          >
            ×
          </span>
        ) : (
          <Search className="ml-1 size-4 shrink-0 opacity-50" />
        )}
      </PopoverTrigger>
      <PopoverContent className="w-[24rem] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput placeholder={placeholder} value={query} onValueChange={setQuery} />
          <CommandList>
            {loading ? (
              <div className="py-6 text-center text-sm text-muted-foreground">
                {query ? "Searching suppliers…" : "Loading suppliers…"}
              </div>
            ) : (
              <>
                <CommandEmpty>No suppliers match your search.</CommandEmpty>
                {filteredSuppliers.length > 0 ? (
                  <CommandGroup>
                    {filteredSuppliers.map((supplier) => (
                      <CommandItem
                        key={supplier.id}
                        value={supplier.name}
                        onSelect={() => handleSelect(supplier)}
                      >
                        <div className="flex flex-col gap-0.5">
                          <span className="font-medium">{supplier.name}</span>
                          <span className="text-xs text-muted-foreground">
                            {supplier.contact_email ?? supplier.phone ?? "No contact info"}
                          </span>
                        </div>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                ) : null}
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}