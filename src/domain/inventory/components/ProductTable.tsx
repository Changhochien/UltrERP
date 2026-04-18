import { useEffect, useState } from "react";
import { ExternalLink, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { DataTable, DataTableToolbar } from "@/components/layout/DataTable";
import { SectionCard } from "@/components/layout/PageLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { buildProductDetailPath } from "@/lib/routes";
import { CategoryCombobox } from "./CategoryCombobox";
import { useProductSearch } from "../hooks/useProductSearch";

interface ProductTableProps {
  warehouseId?: string;
  onProductClick?: (productId: string) => void;
  createdProductKey?: number;
}

export function ProductTable({ warehouseId, onProductClick, createdProductKey }: ProductTableProps) {
  const { t } = useTranslation("common", { keyPrefix: "inventory.productGrid" });
  const navigate = useNavigate();
  const {
    results,
    total,
    page,
    pageSize,
    loading,
    error,
    includeInactive,
    category,
    search,
    nextPage,
    prevPage,
    sortState,
    setSort,
  } = useProductSearch();
  const [query, setQuery] = useState("");

  useEffect(() => {
    search("", warehouseId, 1, sortState ?? undefined, includeInactive, category);
  }, [category, createdProductKey, includeInactive, search, sortState, warehouseId]);

  const handleSearchChange = (value: string) => {
    setQuery(value);
    search(value, warehouseId, 1, sortState ?? undefined, includeInactive, category);
  };

  const handleCategoryChange = (nextCategory: string) => {
    search(query, warehouseId, 1, sortState ?? undefined, includeInactive, nextCategory);
  };

  return (
    <SectionCard
      title={t("productsTitle")}
      description={t("browseProducts")}
      actions={
        <div className="text-sm text-muted-foreground">
          {total > 0 ? t("products", { count: total }) : ""}
        </div>
      }
    >
      <DataTable
        columns={[
          {
            id: "code",
            header: t("code"),
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
            cell: (item) =>
              item.category ?? <span className="text-muted-foreground">—</span>,
          },
          {
            id: "current_stock",
            header: t("stock"),
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
            header: t("status"),
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
          {
            id: "actions",
            header: "",
            cell: (item) => (
              <Button
                type="button"
                variant="ghost"
                size="icon-xs"
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(buildProductDetailPath(item.id, "settings"));
                }}
                title={t("openSettingsPage")}
                aria-label={t("openSettingsPage")}
              >
                <ExternalLink className="size-[15px]" />
              </Button>
            ),
            onClick: (_e, _item) => {},
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
                onClick={() => search(query, warehouseId, page, sortState ?? undefined, includeInactive, category)}
                className="text-sm underline"
              >
                {t("retry")}
              </button>
            </div>
          ) : undefined
        }
        getRowClassName={(row) =>
          row.status === "inactive" ? "bg-muted/20 text-muted-foreground" : undefined
        }
        emptyTitle={query ? t("noProductsFound") : t("noProductsInSystem")}
        emptyDescription={
          query
            ? t("tryDifferentSearchTerm")
            : undefined
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
            <div className="flex flex-col gap-3 md:flex-row md:items-center">
              <div className="relative max-w-64">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  type="search"
                  placeholder={t("searchPlaceholder")}
                  value={query}
                  onChange={(e) => handleSearchChange(e.target.value)}
                  aria-label={t("searchPlaceholder")}
                  className="pl-9"
                />
              </div>
              <div className="min-w-[14rem]">
                <CategoryCombobox
                  value={category}
                  onChange={handleCategoryChange}
                  onClear={() => handleCategoryChange("")}
                  placeholder={t("filterCategory")}
                />
              </div>
              <Button
                type="button"
                variant={includeInactive ? "default" : "outline"}
                size="sm"
                aria-pressed={includeInactive}
                onClick={() => search(query, warehouseId, 1, sortState ?? undefined, !includeInactive, category)}
              >
                {t("showInactive")}
              </Button>
            </div>
          </DataTableToolbar>
        )}
      />
    </SectionCard>
  );
}
