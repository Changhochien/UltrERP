import { useEffect, useState } from "react";
import { Search } from "lucide-react";

import { DataTable, DataTableToolbar } from "@/components/layout/DataTable";
import { SectionCard } from "@/components/layout/PageLayout";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useProductSearch } from "../hooks/useProductSearch";

interface ProductTableProps {
  warehouseId?: string;
  onProductClick?: (productId: string) => void;
}

export function ProductTable({ warehouseId, onProductClick }: ProductTableProps) {
  const {
    results,
    total,
    page,
    pageSize,
    loading,
    error,
    search,
    nextPage,
    prevPage,
    sortState,
    setSort,
  } = useProductSearch();
  const [query, setQuery] = useState("");

  useEffect(() => {
    search("", warehouseId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [warehouseId]);

  const handleSearchChange = (value: string) => {
    setQuery(value);
    search(value, warehouseId);
  };

  return (
    <SectionCard
      title="Products"
      description="Browse all products with current stock levels."
      actions={
        <div className="text-sm text-muted-foreground">
          {total > 0 ? `${total.toLocaleString()} total` : ""}
        </div>
      }
    >
      <DataTable
        columns={[
          {
            id: "code",
            header: "Code",
            sortable: true,
            getSortValue: (item) => item.code,
            cell: (item) => (
              <span className="font-mono text-sm text-amber-600 dark:text-amber-400">
                {item.code}
              </span>
            ),
          },
          {
            id: "name",
            header: "Name",
            sortable: true,
            getSortValue: (item) => item.name,
            cell: (item) => <span className="font-medium">{item.name}</span>,
          },
          {
            id: "category",
            header: "Category",
            sortable: true,
            getSortValue: (item) => item.category ?? "",
            cell: (item) =>
              item.category ?? <span className="text-muted-foreground">—</span>,
          },
          {
            id: "current_stock",
            header: "Stock",
            sortable: true,
            getSortValue: (item) => item.current_stock,
            cell: (item) => (
              <span
                className={
                  item.current_stock === 0
                    ? "font-semibold text-destructive"
                    : item.current_stock < 20
                      ? "font-semibold text-warning"
                      : ""
                }
              >
                {item.current_stock}
              </span>
            ),
          },
          {
            id: "status",
            header: "Status",
            sortable: true,
            getSortValue: (item) => item.status,
            cell: (item) => (
              <Badge
                variant={item.status === "active" ? "success" : "outline"}
                className="normal-case tracking-normal"
              >
                {item.status}
              </Badge>
            ),
          },
        ]}
        data={results}
        loading={loading}
        error={
          error ? (
            <div className="flex items-center gap-3">
              <span>{error}</span>
              <button
                type="button"
                onClick={() => search(query, warehouseId)}
                className="text-sm underline"
              >
                Retry
              </button>
            </div>
          ) : undefined
        }
        emptyTitle={query ? "No matching products" : "No products found"}
        emptyDescription={
          query
            ? "Try a broader keyword or change warehouse scope."
            : "No products exist in the system yet."
        }
        page={page}
        pageSize={pageSize}
        totalItems={total}
        onPageChange={(p) => {
          if (p > page) nextPage();
          else prevPage();
        }}
        sortState={sortState}
        onSortChange={setSort}
        onRowClick={(row) => onProductClick?.(row.id)}
        getRowId={(item) => item.id}
        toolbar={(
          <DataTableToolbar>
            <div className="relative max-w-64">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search by code or name…"
                value={query}
                onChange={(e) => handleSearchChange(e.target.value)}
                aria-label="Search products"
                className="pl-9"
              />
            </div>
          </DataTableToolbar>
        )}
      />
    </SectionCard>
  );
}
