/** Product search with virtualized results list. */

import { Search } from "lucide-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

import { DataTable, DataTableToolbar } from "../../../components/layout/DataTable";
import { SectionCard } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { CategoryCombobox } from "./CategoryCombobox";
import { useProductSearch } from "../hooks/useProductSearch";
import { useWarehouseContext } from "../context/WarehouseContext";

interface ProductSearchProps {
  onProductClick?: (productId: string) => void;
}

export function ProductSearch({ onProductClick }: ProductSearchProps) {
  const { t } = useTranslation("inventory");
  const { query, results, loading, error, includeInactive, categoryId, categoryLabel, search } = useProductSearch();
  const { selectedWarehouse } = useWarehouseContext();
  const trimmedQuery = query.trim();
  const hasSearchQuery = trimmedQuery.length > 0;

  // Load all products on mount
  useEffect(() => {
    search("", selectedWarehouse?.id, 1, undefined, includeInactive, categoryId, categoryLabel);
  }, [categoryId, categoryLabel, includeInactive, search, selectedWarehouse?.id]);

  return (
    <SectionCard title={t("productsTitle")} description={t("browseProducts")}>
      <DataTable
        columns={[
          {
            id: "code",
            header: t("code"),
            sortable: true,
            getSortValue: (item) => item.code,
            cell: (item) => <span className="font-mono text-sm">{item.code}</span>,
          },
          {
            id: "name",
            header: t("name"),
            sortable: true,
            getSortValue: (item) => item.name,
            cell: (item) => <span className="font-medium">{item.name}</span>,
          },
          {
            id: "category",
            header: t("category"),
            sortable: true,
            getSortValue: (item) => item.category ?? "",
            cell: (item) => item.category ?? "—",
          },
          {
            id: "current_stock",
            header: t("stock"),
            sortable: true,
            getSortValue: (item) => item.current_stock,
            cell: (item) => item.current_stock,
          },
          {
            id: "status",
            header: t("status"),
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
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => search(trimmedQuery, selectedWarehouse?.id, 1, undefined, includeInactive, categoryId, categoryLabel)}
            >
              {t("retry")}
            </Button>
          </div>
        ) : undefined}
        getRowClassName={(row) =>
          row.status === "inactive" ? "bg-muted/20 text-muted-foreground" : undefined
        }
        emptyTitle={hasSearchQuery ? t("noProductsFound") : t("noProductsInSystem")}
        emptyDescription={hasSearchQuery ? t("tryDifferentSearchTerm") : undefined}
        toolbar={(
          <DataTableToolbar>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                {t("productGrid.scope")}: {selectedWarehouse?.name ?? t("productGrid.allWarehouses")}
              </p>
            </div>
            <div className="flex w-full max-w-xl flex-col gap-3 md:flex-row md:items-center">
              <div className="relative w-full max-w-md">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  type="search"
                  placeholder={t("searchPlaceholder")}
                  onChange={(event) => search(event.target.value, selectedWarehouse?.id, 1, undefined, includeInactive, categoryId, categoryLabel)}
                  aria-label={t("searchPlaceholder")}
                  className="pl-9"
                />
              </div>
              <div className="min-w-[14rem]">
                <CategoryCombobox
                  value={categoryId || null}
                  valueLabel={categoryLabel || null}
                  onChange={(nextCategoryId, nextCategoryLabel) =>
                    search(trimmedQuery, selectedWarehouse?.id, 1, undefined, includeInactive, nextCategoryId, nextCategoryLabel)
                  }
                  onClear={() => search(trimmedQuery, selectedWarehouse?.id, 1, undefined, includeInactive, "", "")}
                  placeholder={t("filterCategory")}
                />
              </div>
              <Button
                type="button"
                size="sm"
                variant={includeInactive ? "default" : "outline"}
                aria-pressed={includeInactive}
                onClick={() => search(trimmedQuery, selectedWarehouse?.id, 1, undefined, !includeInactive, categoryId, categoryLabel)}
              >
                {t("showInactive")}
              </Button>
            </div>
          </DataTableToolbar>
        )}
        summary={
          results.length > 0
            ? t("products", { count: results.length })
            : undefined
        }
        getRowId={(item) => item.id}
        onRowClick={(row) => onProductClick?.(row.id)}
      />
    </SectionCard>
  );
}
