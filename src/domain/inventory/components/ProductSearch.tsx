/** Product search with virtualized results list. */

import { Search } from "lucide-react";
import { useEffect } from "react";

import { DataTable, DataTableToolbar } from "../../../components/layout/DataTable";
import { SectionCard } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { useProductSearch } from "../hooks/useProductSearch";
import { useWarehouseContext } from "../context/WarehouseContext";

interface ProductSearchProps {
  onProductClick?: (productId: string) => void;
}

export function ProductSearch({ onProductClick }: ProductSearchProps) {
  const { query, results, loading, error, search } = useProductSearch();
  const { selectedWarehouse } = useWarehouseContext();
  const trimmedQuery = query.trim();
  const hasSearchQuery = trimmedQuery.length > 0;

  // Load all products on mount
  useEffect(() => {
    search("", selectedWarehouse?.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <SectionCard title="Product Search" description="Search by code or name and review current stock by warehouse scope.">
      <DataTable
        columns={[
          {
            id: "code",
            header: "Code",
            sortable: true,
            getSortValue: (item) => item.code,
            cell: (item) => <span className="font-mono text-sm">{item.code}</span>,
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
            cell: (item) => item.category ?? "—",
          },
          {
            id: "current_stock",
            header: "Stock",
            sortable: true,
            getSortValue: (item) => item.current_stock,
            cell: (item) => item.current_stock,
          },
          {
            id: "status",
            header: "Status",
            sortable: true,
            getSortValue: (item) => item.status,
            cell: (item) => (
              <Badge variant={item.status === "active" ? "success" : "outline"} className="normal-case tracking-normal">
                {item.status}
              </Badge>
            ),
          },
        ]}
        data={results}
        loading={loading}
        error={error ? (
          <div className="flex items-center gap-3">
            <span>{error}</span>
            <Button type="button" size="sm" variant="outline" onClick={() => search(trimmedQuery, selectedWarehouse?.id)}>
              Retry
            </Button>
          </div>
        ) : undefined}
        emptyTitle={hasSearchQuery ? "No matching products." : "No products found."}
        emptyDescription={hasSearchQuery ? "Try a broader keyword or switch warehouse scope." : "No products exist in the system."}
        toolbar={(
          <DataTableToolbar>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Warehouse scope: {selectedWarehouse?.name ?? "All warehouses"}</p>
            </div>
            <div className="relative w-full max-w-md">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search by code or name…"
                onChange={(event) => search(event.target.value, selectedWarehouse?.id)}
                aria-label="Search products"
                className="pl-9"
              />
            </div>
          </DataTableToolbar>
        )}
        summary={
          results.length > 0
            ? hasSearchQuery
              ? `${results.length} matching products`
              : `${results.length} products`
            : undefined
        }
        getRowId={(item) => item.id}
        onRowClick={(row) => onProductClick?.(row.id)}
      />
    </SectionCard>
  );
}
