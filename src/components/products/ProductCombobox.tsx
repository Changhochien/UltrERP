/** Product autocomplete combobox using Popover + Command — mirrors CustomerCombobox. */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Search } from "lucide-react";

import { ProductForm, type ProductFormSubmitResult } from "../../domain/inventory/components/ProductForm";
import type { ProductResponse, ProductSearchResult, ProductUpdate } from "../../domain/inventory/types";
import { useToast } from "../../hooks/useToast";
import { createProduct, fetchProductDetail, searchProducts } from "../../lib/api/inventory";
import { cn } from "../../lib/utils";
import { Button } from "../ui/button";
import { QuickEntryDialog } from "../ui/QuickEntryDialog";
import { Spinner } from "../ui/Spinner";
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

interface ProductComboboxProps {
  value: string;
  onChange: (productId: string) => void;
  onProductSelected?: (product: ProductSearchResult) => void;
  onClear?: () => void;
  placeholder?: string;
  disabled?: boolean;
  ariaLabel?: string;
  ariaLabelledBy?: string;
}

export function ProductCombobox({
  value,
  onChange,
  onProductSelected,
  onClear,
  placeholder = "Search product by name or code…",
  disabled,
  ariaLabel,
  ariaLabelledBy,
}: ProductComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [products, setProducts] = useState<ProductSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const toast = useToast();

  const loadProducts = useCallback(
    (q: string) => {
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);
      searchProducts(q, { limit: 50, signal: controller.signal })
        .then((response) => {
          if (!controller.signal.aborted) {
            setProducts(response.items);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        });
      return controller;
    },
    [],
  );

  // Load products on popover open, or re-load with query when query changes (debounced)
  useEffect(() => {
    if (!open) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (query.trim().length === 0) {
      loadProducts("");
      return () => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        abortRef.current?.abort();
      };
    }

    debounceRef.current = setTimeout(() => {
      loadProducts(query);
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      abortRef.current?.abort();
    };
  }, [open, query, loadProducts]);

  // If selected product is not in the loaded set, fetch it
  useEffect(() => {
    if (!value || products.some((p) => p.id === value)) return;
    fetchProductDetail(value).then((result) => {
      if (result.ok) {
        setProducts((prev) => {
          if (prev.some((p) => p.id === value)) return prev;
          return [
            ...prev,
            {
              id: result.data.id,
              code: result.data.code,
              name: result.data.name,
              category_id: result.data.category_id,
              category: result.data.category,
              status: result.data.status,
              current_stock: result.data.total_stock ?? 0,
              relevance: 0,
            },
          ];
        });
      }
    });
  }, [value, products]);

  const filtered = useMemo(
    () =>
      products.filter(
        (p) =>
          p.name.toLowerCase().includes(query.toLowerCase()) ||
          p.code.toLowerCase().includes(query),
      ),
    [products, query],
  );

  const selectedProduct = products.find((p) => p.id === value);
  const createInitialValues = useMemo(() => {
    const trimmedQuery = query.trim();
    return trimmedQuery ? { name: trimmedQuery } : undefined;
  }, [query]);

  function handleSelect(productId: string) {
    const product = products.find((p) => p.id === productId);
    if (product) {
      onProductSelected?.(product);
    }
    onChange(productId);
    setOpen(false);
    setQuery("");
  }

  function handleCreateDialogChange(nextOpen: boolean) {
    if (creating) {
      return;
    }

    setCreateDialogOpen(nextOpen);
  }

  function openCreateDialog() {
    setOpen(false);
    setCreateDialogOpen(true);
  }

  function toSearchResult(product: ProductResponse): ProductSearchResult {
    return {
      id: product.id,
      code: product.code,
      name: product.name,
      category_id: product.category_id,
      category: product.category,
      status: product.status,
      current_stock: 0,
      relevance: 0,
    };
  }

  async function handleCreateProduct(values: ProductUpdate): Promise<ProductFormSubmitResult> {
    setCreating(true);

    try {
      const product = await createProduct(values);
      toast.success("Product created", `${product.name} is now selected.`);
      return { ok: true, product };
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to create product";
      toast.error("Failed to create product", message);
      return { ok: false, formError: message };
    } finally {
      setCreating(false);
    }
  }

  function handleCreateSuccess(product: ProductResponse) {
    const createdProduct = toSearchResult(product);
    setProducts((previous) => [createdProduct, ...previous.filter((item) => item.id !== createdProduct.id)]);
    onProductSelected?.(createdProduct);
    onChange(product.id);
    setQuery("");
    setOpen(false);
    setCreateDialogOpen(false);
  }

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger
          render={
            <Button
              type="button"
              variant="outline"
              role="combobox"
              aria-expanded={open}
              aria-label={ariaLabel}
              aria-labelledby={ariaLabelledBy}
              disabled={disabled}
              className={cn(
                "w-full justify-start text-left font-normal",
                !selectedProduct && "text-muted-foreground",
              )}
            />
          }
        >
          {selectedProduct ? (
            <span className="truncate flex-1">
              {selectedProduct.name} ({selectedProduct.code})
            </span>
          ) : (
            <span className="truncate flex-1">{placeholder}</span>
          )}
          {selectedProduct && onClear ? (
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
              aria-label="Clear product filter"
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
                <div className="flex items-center justify-center gap-2 py-6 text-center text-sm text-muted-foreground" aria-busy="true">
                  <Spinner size="sm" className="text-muted-foreground" />
                  <span>{query ? "Searching…" : "Loading products…"}</span>
                </div>
              ) : (
                <>
                  <CommandEmpty>
                    No products match your search.
                  </CommandEmpty>
                  {filtered.length === 0 && query.trim().length > 0 && (
                    <CommandGroup>
                      <CommandItem onSelect={openCreateDialog}>
                        <div className="flex items-center gap-2">
                          <span>Create new product</span>
                        </div>
                      </CommandItem>
                    </CommandGroup>
                  )}
                  {filtered.length > 0 && (
                    <CommandGroup>
                      {filtered.map((product) => (
                        <CommandItem
                          key={product.id}
                          value={product.id}
                          onSelect={() => handleSelect(product.id)}
                        >
                          <div className="flex flex-col gap-0.5">
                            <span className="font-medium">{product.name}</span>
                            <span className="text-xs text-muted-foreground">
                              {product.code}
                              {" · "}
                              {product.current_stock > 0
                                ? `${product.current_stock} avail`
                                : "Out of stock"}
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
        title="Create new product"
        description="Add the product here and select it without leaving the current form."
        size="lg"
        busy={creating}
      >
        <ProductForm
          initialValues={createInitialValues}
          onSubmit={handleCreateProduct}
          onSuccess={handleCreateSuccess}
          onCancel={() => handleCreateDialogChange(false)}
          submitLabel="Create Product"
          submittingLabel="Creating..."
        />
      </QuickEntryDialog>
    </>
  );
}
