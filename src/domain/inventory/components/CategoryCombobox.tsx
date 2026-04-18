import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { PlusCircle, Search } from "lucide-react";

import { createCategory, listCategories } from "../../../lib/api/inventory";
import { cn } from "../../../lib/utils";
import type { Category } from "../types";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
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

interface CategoryComboboxProps {
  value: string;
  onChange: (categoryName: string) => void;
  onClear?: () => void;
  placeholder?: string;
  disabled?: boolean;
  activeOnly?: boolean;
  allowCreate?: boolean;
  inputId?: string;
  ariaLabel?: string;
  ariaLabelledBy?: string;
}

export function CategoryCombobox({
  value,
  onChange,
  onClear,
  placeholder = "Search category…",
  disabled,
  activeOnly = true,
  allowCreate = false,
  inputId,
  ariaLabel,
  ariaLabelledBy,
}: CategoryComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [createPending, setCreatePending] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadCategories = useCallback(
    (nextQuery: string) => {
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);

      listCategories({
        q: nextQuery.trim() || undefined,
        activeOnly,
        limit: 50,
        signal: controller.signal,
      })
        .then((response) => {
          if (!controller.signal.aborted) {
            setCategories(response.items);
          }
        })
        .catch(() => {
          if (!controller.signal.aborted) {
            setCategories([]);
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
      loadCategories("");
      return () => {
        abortRef.current?.abort();
      };
    }

    debounceRef.current = setTimeout(() => {
      loadCategories(query);
    }, 250);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      abortRef.current?.abort();
    };
  }, [loadCategories, open, query]);

  useEffect(() => {
    setCreateName(query.trim());
    setCreateError(null);
  }, [query]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setCreateName("");
      setCreateError(null);
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

  const filteredCategories = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return categories;
    }

    return categories.filter((category) => category.name.toLowerCase().includes(normalizedQuery));
  }, [categories, query]);

  const hasExactMatch = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return false;
    }

    return categories.some((category) => category.name.toLowerCase() === normalizedQuery);
  }, [categories, query]);

  async function handleCreateCategory() {
    const name = createName.trim() || query.trim();
    if (!name) {
      setCreateError("Category name is required.");
      return;
    }

    setCreatePending(true);
    setCreateError(null);
    const result = await createCategory({ name });
    setCreatePending(false);

    if (!result.ok) {
      setCreateError(result.error);
      return;
    }

    setCategories((current) => {
      if (current.some((category) => category.id === result.data.id)) {
        return current;
      }
      return [result.data, ...current];
    });
    onChange(result.data.name);
    setOpen(false);
  }

  function handleSelect(categoryName: string) {
    onChange(categoryName);
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
              !value && "text-muted-foreground",
            )}
          />
        }
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
            aria-label="Clear category"
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
                {query ? "Searching categories…" : "Loading categories…"}
              </div>
            ) : (
              <>
                <CommandEmpty>No categories match your search.</CommandEmpty>
                {filteredCategories.length > 0 ? (
                  <CommandGroup>
                    {filteredCategories.map((category) => (
                      <CommandItem
                        key={category.id}
                        value={category.name}
                        onSelect={() => handleSelect(category.name)}
                      >
                        <div className="flex flex-col gap-0.5">
                          <span className="font-medium">{category.name}</span>
                          <span className="text-xs text-muted-foreground">
                            {category.is_active ? "Active" : "Inactive"}
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
        {allowCreate && query.trim().length > 0 && !hasExactMatch ? (
          <div className="space-y-2 border-t border-border/70 p-3">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <PlusCircle className="size-4" />
              Create category
            </div>
            <Input
              value={createName}
              onChange={(event) => setCreateName(event.target.value)}
              placeholder="New category name"
              disabled={createPending}
            />
            {createError ? <p className="text-sm text-destructive">{createError}</p> : null}
            <Button
              type="button"
              size="sm"
              onClick={handleCreateCategory}
              disabled={createPending}
            >
              {createPending ? "Creating…" : "Create category"}
            </Button>
          </div>
        ) : null}
      </PopoverContent>
    </Popover>
  );
}