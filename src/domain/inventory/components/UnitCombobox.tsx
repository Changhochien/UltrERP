import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Search } from "lucide-react";

import { Button } from "../../../components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "../../../components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "../../../components/ui/popover";
import { listUnits } from "../../../lib/api/inventory";
import { cn } from "../../../lib/utils";
import type { UnitOfMeasure } from "../types";

interface UnitComboboxProps {
  value: string;
  onChange: (unitCode: string) => void;
  onClear?: () => void;
  placeholder?: string;
  disabled?: boolean;
  activeOnly?: boolean;
  inputId?: string;
  ariaLabel?: string;
  ariaLabelledBy?: string;
}

export function UnitCombobox({
  value,
  onChange,
  onClear,
  placeholder = "Search unit…",
  disabled,
  activeOnly = true,
  inputId,
  ariaLabel,
  ariaLabelledBy,
}: UnitComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [units, setUnits] = useState<UnitOfMeasure[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadUnits = useCallback(
    (nextQuery: string) => {
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);

      listUnits({
        q: nextQuery.trim() || undefined,
        activeOnly,
        limit: 50,
        signal: controller.signal,
      })
        .then((response) => {
          if (!controller.signal.aborted) {
            setUnits(response.items);
          }
        })
        .catch(() => {
          if (!controller.signal.aborted) {
            setUnits([]);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        });

      return controller;
    },
    [activeOnly],
  );

  useEffect(() => {
    if (!open) {
      return;
    }

    abortRef.current?.abort();
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (query.trim().length === 0) {
      loadUnits("");
      return () => {
        abortRef.current?.abort();
      };
    }

    debounceRef.current = setTimeout(() => {
      loadUnits(query);
    }, 250);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      abortRef.current?.abort();
    };
  }, [loadUnits, open, query]);

  useEffect(() => {
    if (!open) {
      setQuery("");
    }
  }, [open]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  const filteredUnits = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return units;
    }

    return units.filter(
      (unit) =>
        unit.code.toLowerCase().includes(normalizedQuery)
        || unit.name.toLowerCase().includes(normalizedQuery),
    );
  }, [query, units]);

  function handleSelect(unitCode: string) {
    onChange(unitCode);
    setOpen(false);
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={(
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
              !value && "text-muted-foreground",
            )}
          />
        )}
      >
        {value ? <span className="truncate flex-1">{value}</span> : <span className="truncate flex-1">{placeholder}</span>}
        {value && onClear ? (
          <span
            role="button"
            tabIndex={0}
            onClick={(event) => {
              event.stopPropagation();
              onClear();
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.stopPropagation();
                onClear();
              }
            }}
            className="ml-1 cursor-pointer rounded-sm opacity-70 hover:opacity-100 focus:outline-none"
            aria-label="Clear unit"
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
                {query ? "Searching units…" : "Loading units…"}
              </div>
            ) : (
              <>
                <CommandEmpty>No units match your search.</CommandEmpty>
                {filteredUnits.length > 0 ? (
                  <CommandGroup>
                    {filteredUnits.map((unit) => (
                      <CommandItem
                        key={unit.id}
                        value={`${unit.code} ${unit.name}`}
                        onSelect={() => handleSelect(unit.code)}
                      >
                        <div className="flex flex-col gap-0.5">
                          <span className="font-medium">{unit.code}</span>
                          <span className="text-xs text-muted-foreground">
                            {unit.name}
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